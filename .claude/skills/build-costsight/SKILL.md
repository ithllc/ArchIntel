---
name: build-costsight
description: Build the CostSight feature — cloud cost estimation from architecture diagrams with conversational refinement. Uses Gemini 1.5 Pro multimodal + Vercel AI SDK useChat + tool calling.
user_invocable: true
---

# Build CostSight Feature

You are building the cost estimation feature of ArchIntel. This feature identifies cloud services from an architecture diagram, estimates monthly costs, and provides a conversational interface for refining estimates based on traffic/scale inputs.

## Prerequisites
- The project has been scaffolded (run `/scaffold-app` first)
- `lib/pricing-data.ts` exists with cloud pricing data
- Supabase tables exist (cost_estimates, chat_logs)

## File 1: app/api/chat/route.ts

Create the chat-compatible API route using `useChat` protocol:

```typescript
import { streamText, tool } from 'ai';
import { google } from '@ai-sdk/google';
import { z } from 'zod';
import { CLOUD_PRICING } from '@/lib/pricing-data';
import { supabase } from '@/lib/supabase';

export const maxDuration = 60;

export async function POST(req: Request) {
  try {
    const { messages, data } = await req.json();

    // If there's a diagram image in the data, include it in the first message
    const systemMessage = `You are CostSight, an expert cloud FinOps analyst within the ArchIntel platform. Your job is to:

1. Analyze architecture diagrams to identify all cloud services/components
2. Ask the user clarifying questions about scale (MAU, requests/month, data volume, regions)
3. Use the calculateCost tool to produce accurate monthly cost estimates
4. Suggest cost optimizations

Available pricing data services: ${Object.keys(CLOUD_PRICING).join(', ')}

When you identify services from a diagram, IMMEDIATELY use identifyServices to catalog them, then ask clarifying questions about traffic. Once you have enough info, use calculateCost to produce the estimate.

Format cost breakdowns as clean tables. Always end with 1-2 optimization suggestions.`;

    const result = streamText({
      model: google('gemini-1.5-pro'),
      system: systemMessage,
      messages,
      maxSteps: 5,
      tools: {
        identifyServices: tool({
          description: 'Identify and catalog cloud services found in the architecture diagram',
          parameters: z.object({
            services: z.array(z.object({
              name: z.string().describe('Service name as shown in diagram'),
              type: z.string().describe('Matched service type from pricing data'),
              count: z.number().describe('Number of instances'),
              notes: z.string().describe('Any relevant notes about configuration'),
            })),
          }),
          execute: async ({ services }) => {
            return {
              identified: services.length,
              services: services.map(s => ({
                ...s,
                unitPricing: CLOUD_PRICING[s.type] || null,
              })),
              message: `Identified ${services.length} services. Ready for cost calculation once traffic details are provided.`,
            };
          },
        }),

        calculateCost: tool({
          description: 'Calculate monthly cloud cost based on identified services and traffic parameters',
          parameters: z.object({
            services: z.array(z.object({
              name: z.string(),
              type: z.string(),
              count: z.number(),
              hoursPerMonth: z.number().describe('Expected compute hours per month (730 = always on)'),
              gbPerMonth: z.number().describe('Expected data transfer/storage in GB per month'),
            })),
            notes: z.string().optional().describe('Any additional context'),
          }),
          execute: async ({ services, notes }) => {
            const breakdown = services.map(service => {
              const pricing = CLOUD_PRICING[service.type];
              if (!pricing) {
                return {
                  name: service.name,
                  type: service.type,
                  monthlyCost: 0,
                  note: 'Unknown service type — estimate not available',
                };
              }

              const computeCost = pricing.perHour * service.hoursPerMonth * service.count;
              const dataCost = pricing.perGB * service.gbPerMonth * service.count;
              const total = computeCost + dataCost;

              return {
                name: service.name,
                type: service.type,
                description: pricing.description,
                count: service.count,
                computeCost: Math.round(computeCost * 100) / 100,
                dataCost: Math.round(dataCost * 100) / 100,
                monthlyCost: Math.round(total * 100) / 100,
              };
            });

            const totalMonthlyCost = breakdown.reduce((sum, s) => sum + s.monthlyCost, 0);

            // Save to Supabase
            await supabase.from('cost_estimates').insert({
              services: breakdown,
              total_monthly_cost: totalMonthlyCost,
              diagram_hash: 'demo',
            }).then(() => {}).catch(() => {});

            return {
              breakdown,
              totalMonthlyCost: Math.round(totalMonthlyCost * 100) / 100,
              annualEstimate: Math.round(totalMonthlyCost * 12 * 100) / 100,
            };
          },
        }),
      },
    });

    return result.toDataStreamResponse();
  } catch (error) {
    console.error('Chat error:', error);
    return new Response(
      JSON.stringify({ error: 'Chat failed. Please try again.' }),
      { status: 500, headers: { 'Content-Type': 'application/json' } }
    );
  }
}
```

## File 2: components/cost-panel.tsx

```typescript
'use client';

import { useChat } from '@ai-sdk/react';
import { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import { DollarSign, Send, Loader2, TrendingDown } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';

interface CostPanelProps {
  diagramFile: File | null;
}

export function CostPanel({ diagramFile }: CostPanelProps) {
  const [hasStarted, setHasStarted] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  const { messages, input, handleInputChange, handleSubmit, isLoading, append } = useChat({
    api: '/api/chat',
    maxSteps: 5,
  });

  const startAnalysis = async () => {
    if (!diagramFile) return;
    setHasStarted(true);

    // Convert file to base64 and send as first message with image
    const buffer = await diagramFile.arrayBuffer();
    const base64 = Buffer.from(buffer).toString('base64');

    append({
      role: 'user',
      content: 'Analyze this architecture diagram and identify all cloud services. Then ask me about our expected traffic so you can estimate costs.',
      experimental_attachments: [
        {
          name: diagramFile.name,
          contentType: diagramFile.type,
          url: `data:${diagramFile.type};base64,${base64}`,
        },
      ],
    });
  };

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div className="flex flex-col h-full space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <DollarSign className="h-5 w-5 text-green-400" />
          <h2 className="text-lg font-semibold text-white">Cost Estimation</h2>
        </div>
        {!hasStarted && (
          <button
            onClick={startAnalysis}
            disabled={!diagramFile}
            className="px-4 py-2 bg-green-600 hover:bg-green-700 disabled:bg-gray-700 text-white rounded-lg flex items-center gap-2 transition-colors"
          >
            <TrendingDown className="h-4 w-4" />
            Estimate Costs
          </button>
        )}
      </div>

      <ScrollArea className="flex-1 h-[400px]">
        <div className="space-y-4 p-1">
          {messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <Card
                className={`max-w-[85%] p-3 ${
                  message.role === 'user'
                    ? 'bg-green-900/30 border-green-700'
                    : 'bg-gray-900 border-gray-700'
                }`}
              >
                <ReactMarkdown className="prose prose-invert prose-sm max-w-none">
                  {message.content}
                </ReactMarkdown>
              </Card>
            </div>
          ))}
          {isLoading && (
            <div className="flex items-center gap-2 text-gray-400">
              <Loader2 className="h-4 w-4 animate-spin" />
              <span className="text-sm">Calculating...</span>
            </div>
          )}
          <div ref={scrollRef} />
        </div>
      </ScrollArea>

      {hasStarted && (
        <form onSubmit={handleSubmit} className="flex gap-2">
          <input
            value={input}
            onChange={handleInputChange}
            placeholder="e.g., We expect 1M requests/month with 500GB storage..."
            className="flex-1 px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-green-500"
          />
          <button
            type="submit"
            disabled={isLoading || !input.trim()}
            className="px-4 py-2 bg-green-600 hover:bg-green-700 disabled:bg-gray-700 text-white rounded-lg transition-colors"
          >
            <Send className="h-4 w-4" />
          </button>
        </form>
      )}
    </div>
  );
}
```

## Important Notes

- The `useChat` hook from `@ai-sdk/react` handles the streaming protocol automatically.
- `experimental_attachments` sends images to the API route — the chat route must handle multimodal messages.
- `maxSteps: 5` allows the model to: see diagram → call identifyServices → ask questions → user responds → call calculateCost → summarize.
- The pricing data is intentionally mocked/simplified. For the demo, the important thing is that the tool EXECUTES and returns structured data that the model formats nicely.
- Cost breakdown should render as a clean markdown table in the chat.

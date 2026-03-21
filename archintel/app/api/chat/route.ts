import { streamText, tool } from 'ai';
import { google } from '@ai-sdk/google';
import { z } from 'zod';
import { CLOUD_PRICING } from '@/lib/pricing-data';

export const maxDuration = 60;

export async function POST(req: Request) {
  try {
    const { messages } = await req.json();

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
      tools: {
        identifyServices: tool({
          description: 'Identify and catalog cloud services found in the architecture diagram',
          inputSchema: z.object({
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
          inputSchema: z.object({
            services: z.array(z.object({
              name: z.string(),
              type: z.string(),
              count: z.number(),
              hoursPerMonth: z.number().describe('Expected compute hours per month (730 = always on)'),
              gbPerMonth: z.number().describe('Expected data transfer/storage in GB per month'),
            })),
            notes: z.string().optional().describe('Any additional context'),
          }),
          execute: async ({ services }) => {
            const breakdown = services.map(service => {
              const pricing = CLOUD_PRICING[service.type];
              if (!pricing) {
                return {
                  name: service.name,
                  type: service.type,
                  monthlyCost: 0,
                  note: 'Unknown service type',
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

            return {
              breakdown,
              totalMonthlyCost: Math.round(totalMonthlyCost * 100) / 100,
              annualEstimate: Math.round(totalMonthlyCost * 12 * 100) / 100,
            };
          },
        }),
      },
    });

    return result.toUIMessageStreamResponse();
  } catch (error) {
    console.error('Chat error:', error);
    return new Response(
      JSON.stringify({ error: 'Chat failed. Please try again.' }),
      { status: 500, headers: { 'Content-Type': 'application/json' } }
    );
  }
}

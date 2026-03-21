---
name: build-threatops
description: Build the ThreatOps feature — STRIDE threat analysis from architecture diagrams with Terraform remediation generation. Uses Gemini 1.5 Pro multimodal + Vercel AI SDK streamText + tool calling.
user_invocable: true
---

# Build ThreatOps Feature

You are building the security analysis feature of ArchIntel. This feature takes an uploaded architecture diagram, analyzes it with Gemini 1.5 Pro's vision capabilities, produces a STRIDE threat model, and generates Terraform remediation policies.

## Prerequisites
- The project has been scaffolded (run `/scaffold-app` first)
- Supabase tables exist (threat_models, generated_policies)

## File 1: app/api/threat-model/route.ts

Create the streaming API route:

```typescript
import { streamText, tool } from 'ai';
import { google } from '@ai-sdk/google';
import { z } from 'zod';
import { supabase } from '@/lib/supabase';

export const maxDuration = 60;

export async function POST(req: Request) {
  try {
    const formData = await req.formData();
    const image = formData.get('diagram') as File;

    if (!image) {
      return new Response('No diagram uploaded', { status: 400 });
    }

    const buffer = Buffer.from(await image.arrayBuffer());
    const base64 = buffer.toString('base64');
    const mimeType = image.type || 'image/png';

    const result = streamText({
      model: google('gemini-1.5-pro'),
      maxSteps: 5,
      messages: [
        {
          role: 'user',
          content: [
            {
              type: 'image',
              image: buffer,
              mimeType,
            },
            {
              type: 'text',
              text: `You are ArchIntel, an expert security architect. Analyze this architecture diagram and produce a comprehensive STRIDE threat model.

For each identified component and data flow in the diagram:

1. **Spoofing** — Can an attacker impersonate a component?
2. **Tampering** — Can data be modified in transit or at rest?
3. **Repudiation** — Are actions logged and attributable?
4. **Information Disclosure** — Can sensitive data leak?
5. **Denial of Service** — Can a component be overwhelmed?
6. **Elevation of Privilege** — Can access controls be bypassed?

Format your analysis as:
## Architecture Overview
(Brief description of what you see in the diagram)

## STRIDE Threat Analysis

### 🔴 Critical Threats
(List critical threats with severity HIGH)

### 🟡 Medium Threats
(List medium threats)

### 🟢 Low Threats
(List low/informational threats)

## Remediation Summary
(Brief summary of recommended fixes)

After your analysis, use the generateTerraform tool to create IAM/security policies for EACH critical threat identified.`,
            },
          ],
        },
      ],
      tools: {
        generateTerraform: tool({
          description: 'Generate a Terraform security policy file to remediate an identified threat. Call this for each critical vulnerability found.',
          parameters: z.object({
            threatName: z.string().describe('Name of the threat being remediated'),
            filename: z.string().describe('Terraform filename, e.g., iam_policy.tf'),
            content: z.string().describe('Complete Terraform HCL content'),
            severity: z.enum(['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']),
          }),
          execute: async ({ threatName, filename, content, severity }) => {
            // Save to Supabase
            const { data, error } = await supabase
              .from('generated_policies')
              .insert({
                filename,
                content,
                threat_name: threatName,
                severity,
              })
              .select()
              .single();

            if (error) {
              console.error('Supabase error:', error);
              return { saved: false, filename, error: error.message };
            }

            return { saved: true, filename, id: data?.id };
          },
        }),
      },
    });

    return result.toDataStreamResponse();
  } catch (error) {
    console.error('Threat model error:', error);
    return new Response(
      JSON.stringify({ error: 'Failed to analyze diagram. Please try again.' }),
      { status: 500, headers: { 'Content-Type': 'application/json' } }
    );
  }
}
```

## File 2: components/threat-panel.tsx

Build the threat analysis display component:

```typescript
'use client';

import { useCompletion } from '@ai-sdk/react';
import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { SyntaxHighlighter } from 'react-syntax-highlighter';
import { atomOneDark } from 'react-syntax-highlighter/dist/esm/styles/hljs';
import { Shield, AlertTriangle, FileCode, Loader2 } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';

interface ThreatPanelProps {
  diagramFile: File | null;
}

export function ThreatPanel({ diagramFile }: ThreatPanelProps) {
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [streamedText, setStreamedText] = useState('');
  const [terraformFiles, setTerraformFiles] = useState<Array<{ filename: string; content: string }>>([]);
  const [error, setError] = useState<string | null>(null);

  const analyze = async () => {
    if (!diagramFile) return;

    setIsAnalyzing(true);
    setStreamedText('');
    setTerraformFiles([]);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('diagram', diagramFile);

      const response = await fetch('/api/threat-model', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) throw new Error('Analysis failed');

      // Handle the AI SDK data stream
      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      while (reader) {
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value);
        // Parse AI SDK stream format and update state
        setStreamedText(prev => prev + chunk);
      }
    } catch (err) {
      setError('Failed to analyze diagram. Please try again.');
    } finally {
      setIsAnalyzing(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Shield className="h-5 w-5 text-red-400" />
          <h2 className="text-lg font-semibold text-white">STRIDE Threat Analysis</h2>
        </div>
        <button
          onClick={analyze}
          disabled={!diagramFile || isAnalyzing}
          className="px-4 py-2 bg-red-600 hover:bg-red-700 disabled:bg-gray-700 text-white rounded-lg flex items-center gap-2 transition-colors"
        >
          {isAnalyzing ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Analyzing...
            </>
          ) : (
            <>
              <AlertTriangle className="h-4 w-4" />
              Run Analysis
            </>
          )}
        </button>
      </div>

      {error && (
        <div className="p-3 bg-red-900/30 border border-red-700 rounded-lg text-red-300 text-sm">
          {error}
        </div>
      )}

      <ScrollArea className="h-[500px]">
        {streamedText && (
          <Card className="p-4 bg-gray-900 border-gray-700">
            <ReactMarkdown className="prose prose-invert max-w-none">
              {streamedText}
            </ReactMarkdown>
          </Card>
        )}
      </ScrollArea>

      {terraformFiles.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <FileCode className="h-5 w-5 text-green-400" />
            <h3 className="text-md font-semibold text-white">Generated Terraform Policies</h3>
          </div>
          {terraformFiles.map((tf, i) => (
            <Card key={i} className="bg-gray-900 border-gray-700 overflow-hidden">
              <div className="px-3 py-2 bg-gray-800 border-b border-gray-700 flex items-center gap-2">
                <Badge variant="outline" className="text-green-400 border-green-700">
                  {tf.filename}
                </Badge>
              </div>
              <SyntaxHighlighter language="hcl" style={atomOneDark} className="!m-0">
                {tf.content}
              </SyntaxHighlighter>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
```

## Important Notes
- The streaming response uses Vercel AI SDK's `toDataStreamResponse()` — use the `useChat` or `useCompletion` hooks on the frontend for proper stream parsing.
- Tool results (Terraform files) come through the stream as tool call events. Parse them from the stream to populate the terraform panel.
- The Supabase insert in the tool can fail silently in the demo — the key is that the tool EXECUTES and the Terraform appears in the UI.
- For the hackathon demo, the quality of the STRIDE analysis is driven entirely by the prompt. The prompt above is battle-tested.

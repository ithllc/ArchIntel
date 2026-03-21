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
    const mimeType = image.type || 'image/png';
    const diagramHash = `${image.name}-${image.size}-${Date.now()}`;

    // Create threat model record in Supabase
    const { data: threatModelRow } = await supabase
      .from('threat_models')
      .insert({ diagram_hash: diagramHash, stride_analysis: {} })
      .select('id')
      .single();

    const threatModelId = threatModelRow?.id;

    const result = streamText({
      model: google('gemini-1.5-pro'),
      messages: [
        {
          role: 'user',
          content: [
            {
              type: 'image',
              image: `data:${mimeType};base64,${buffer.toString('base64')}`,
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

### Critical Threats
(List critical threats with severity HIGH)

### Medium Threats
(List medium threats)

### Low Threats
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
          inputSchema: z.object({
            threatName: z.string().describe('Name of the threat being remediated'),
            filename: z.string().describe('Terraform filename, e.g., iam_policy.tf'),
            content: z.string().describe('Complete Terraform HCL content'),
            severity: z.enum(['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']),
          }),
          execute: async ({ threatName, filename, content, severity }) => {
            // Save generated policy to Supabase
            await supabase.from('generated_policies').insert({
              threat_model_id: threatModelId,
              threat_name: threatName,
              severity,
              filename,
              content,
            });

            return { saved: true, filename, threatName, severity, content };
          },
        }),
      },
      onFinish: async ({ text }) => {
        // Update threat model with final STRIDE analysis
        if (threatModelId) {
          await supabase
            .from('threat_models')
            .update({ stride_analysis: { raw_text: text } })
            .eq('id', threatModelId);
        }
      },
    });

    return result.toUIMessageStreamResponse();
  } catch (error) {
    console.error('Threat model error:', error);
    return new Response(
      JSON.stringify({ error: 'Failed to analyze diagram. Please try again.' }),
      { status: 500, headers: { 'Content-Type': 'application/json' } }
    );
  }
}

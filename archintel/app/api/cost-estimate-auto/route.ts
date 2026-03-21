import { generateText } from 'ai';
import { google } from '@ai-sdk/google';
import { CLOUD_PRICING } from '@/lib/pricing-data';
import { supabase } from '@/lib/supabase';

export const maxDuration = 60;

export async function POST(req: Request) {
  try {
    const formData = await req.formData();
    const image = formData.get('diagram') as File;

    if (!image) {
      return new Response(
        JSON.stringify({ error: 'No diagram uploaded' }),
        { status: 400, headers: { 'Content-Type': 'application/json' } }
      );
    }

    const buffer = Buffer.from(await image.arrayBuffer());

    const pricingRef = Object.entries(CLOUD_PRICING)
      .map(([key, val]) => `${key}: $${val.perHour}/hr compute, $${val.perGB}/GB data (${val.description})`)
      .join('\n');

    const result = await generateText({
      model: google('gemini-2.5-flash'),
      messages: [
        {
          role: 'user',
          content: [
            { type: 'image', image: buffer },
            {
              type: 'text',
              text: `You are CostSight, an expert cloud FinOps analyst. Analyze this architecture diagram and produce a cost estimate.

Use these pricing rates:
${pricingRef}

Default assumptions: 730 compute hours/month (always-on), 100GB data/month per service unless the diagram suggests otherwise.

You MUST respond with ONLY valid JSON in this exact format (no markdown, no code fences):
{
  "text": "A markdown summary of the cost analysis with optimization suggestions",
  "breakdown": [
    { "name": "Service Name", "type": "pricing-key", "description": "Service description", "count": 1, "computeCost": 0.00, "dataCost": 0.00, "monthlyCost": 0.00 }
  ],
  "totalMonthlyCost": 0.00,
  "annualEstimate": 0.00
}

Identify all cloud services visible in the diagram, calculate costs using the pricing rates above, and include optimization suggestions in the text field.`,
            },
          ],
        },
      ],
    });

    // Parse the JSON response
    let parsed: { text: string; breakdown: Array<Record<string, unknown>>; totalMonthlyCost: number; annualEstimate: number };
    try {
      // Strip any markdown code fences if present
      let cleanText = result.text.trim();
      if (cleanText.startsWith('```')) {
        cleanText = cleanText.replace(/^```(?:json)?\n?/, '').replace(/\n?```$/, '');
      }
      parsed = JSON.parse(cleanText);
    } catch {
      // If JSON parsing fails, return the raw text with empty breakdown
      parsed = {
        text: result.text,
        breakdown: [],
        totalMonthlyCost: 0,
        annualEstimate: 0,
      };
    }

    // Save to Supabase
    if (parsed.breakdown.length > 0) {
      await supabase.from('cost_estimates').insert({
        diagram_hash: `auto-cost-${Date.now()}`,
        services: parsed.breakdown,
        total_monthly_cost: parsed.totalMonthlyCost,
      });
    }

    return new Response(JSON.stringify(parsed), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  } catch (error) {
    console.error('Auto cost estimation error:', error);
    return new Response(
      JSON.stringify({ error: 'Cost estimation failed. Please try again.' }),
      { status: 500, headers: { 'Content-Type': 'application/json' } }
    );
  }
}

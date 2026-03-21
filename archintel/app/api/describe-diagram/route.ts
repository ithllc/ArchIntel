import { generateText } from 'ai';
import { google } from '@ai-sdk/google';

export const maxDuration = 30;

export async function POST(req: Request) {
  try {
    const formData = await req.formData();
    const image = formData.get('diagram') as File;

    if (!image) {
      return new Response(JSON.stringify({ error: 'No diagram' }), { status: 400 });
    }

    const buffer = Buffer.from(await image.arrayBuffer());

    const result = await generateText({
      model: google('gemini-2.5-flash'),
      messages: [
        {
          role: 'user',
          content: [
            { type: 'image', image: buffer },
            {
              type: 'text',
              text: `Describe this architecture diagram in detail. List every component, service, database, queue, load balancer, and connection you can see. Include service names, cloud providers (AWS/GCP/Azure), data flows, and protocols. Be thorough — this description will be used by a voice AI to discuss the architecture with the user. Format as a structured text description, not markdown.`,
            },
          ],
        },
      ],
    });

    return new Response(JSON.stringify({ description: result.text }), {
      headers: { 'Content-Type': 'application/json' },
    });
  } catch (error) {
    console.error('Describe diagram error:', error);
    return new Response(JSON.stringify({ error: 'Failed to describe diagram' }), { status: 500 });
  }
}

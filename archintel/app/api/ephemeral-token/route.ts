import { NextResponse } from 'next/server';

export async function GET() {
  try {
    // Note: Gemini ephemeral tokens (v1alpha authTokens.create) are not yet
    // supported for BidiGenerateContent (WebSocket). The Live API requires
    // a direct API key. This is acceptable for the hackathon demo since the
    // key is scoped to this project only.
    return NextResponse.json({
      apiKey: process.env.GOOGLE_GENERATIVE_AI_API_KEY,
      model: 'gemini-2.5-flash-native-audio-latest',
    });
  } catch (error) {
    console.error('Token generation error:', error);
    return NextResponse.json({ error: 'Failed to generate token' }, { status: 500 });
  }
}

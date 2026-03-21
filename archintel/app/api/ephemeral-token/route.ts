import { NextResponse } from 'next/server';

export async function GET() {
  try {
    return NextResponse.json({
      apiKey: process.env.GOOGLE_GENERATIVE_AI_API_KEY,
      model: 'gemini-2.5-flash-native-audio-latest',
    });
  } catch (error) {
    console.error('Token generation error:', error);
    return NextResponse.json({ error: 'Failed to generate token' }, { status: 500 });
  }
}

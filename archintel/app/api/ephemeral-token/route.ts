import { GoogleGenAI } from '@google/genai';
import { NextResponse } from 'next/server';

export async function GET() {
  try {
    const client = new GoogleGenAI({
      apiKey: process.env.GOOGLE_GENERATIVE_AI_API_KEY!,
      httpOptions: { apiVersion: 'v1alpha' },
    });

    const now = new Date();
    const expireTime = new Date(now.getTime() + 30 * 60 * 1000); // 30 min
    const newSessionExpireTime = new Date(now.getTime() + 2 * 60 * 1000); // 2 min to start

    const resp = await client.authTokens.create({
      config: {
        uses: 1,
        expireTime: expireTime.toISOString(),
        newSessionExpireTime: newSessionExpireTime.toISOString(),
      },
    });

    const ephemeralToken = resp.name!.split('/')[1];

    return NextResponse.json({
      token: ephemeralToken,
      model: 'gemini-2.5-flash-native-audio-latest',
    });
  } catch (error) {
    console.error('Ephemeral token error:', error);
    return NextResponse.json({ error: 'Failed to generate token' }, { status: 500 });
  }
}

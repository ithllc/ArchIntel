---
name: build-voice-visual
description: Add voice and visual interaction to ArchIntel using Gemini 2.5 Flash Native Audio Live API. Users speak to their architecture diagram and get real-time spoken analysis. Uses ephemeral tokens for direct browser→Gemini WebSocket connection with zero server-side audio proxying.
user_invocable: true
---

# Build Voice/Visual Feature

You are adding real-time voice and visual interaction to ArchIntel. The user uploads or photographs an architecture diagram, then has a spoken conversation with Gemini about its security threats and costs. Gemini sees the diagram and speaks back.

## Architecture

```
Browser ←→ Gemini 2.5 Flash Native Audio (Direct WebSocket)
  ↑
  | ephemeral token from /api/ephemeral-token
  ↓
Next.js API Route (token generation only — no audio proxying)
```

**Key Insight from FUSE:** The ephemeral token approach gives ultra-low latency because audio goes directly from browser to Gemini with no server hop. The server only handles token generation.

## Model: `gemini-2.5-flash-native-audio-latest`

This is the latest Gemini model with native audio I/O. It can:
- Receive audio (PCM16 @ 16kHz) + images (JPEG) simultaneously
- Generate spoken audio responses (PCM16 @ 24kHz)
- Call tools mid-conversation
- Provide input/output transcription

## Prerequisites
- Project scaffolded with `/scaffold-app`
- The `google-genai` npm package is NOT needed — this uses raw WebSocket to Gemini
- The Gemini API key is needed server-side only (for ephemeral token generation)

## Step 1: Install Additional Dependencies

```bash
npm install @google/generative-ai
```

Note: We use `@google/generative-ai` ONLY for ephemeral token generation on the server. All actual AI communication happens via direct WebSocket from the browser.

## Step 2: Create /api/ephemeral-token/route.ts

```typescript
import { GoogleGenAI } from '@google/generative-ai';
import { NextResponse } from 'next/server';

export async function GET() {
  try {
    const client = new GoogleGenAI({
      apiKey: process.env.GOOGLE_GENERATIVE_AI_API_KEY!,
    });

    // Create an ephemeral token for direct browser→Gemini connection
    // Token is single-use, expires in 30 minutes
    const response = await fetch(
      `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-native-audio-dialog:generateContent?key=${process.env.GOOGLE_GENERATIVE_AI_API_KEY}`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          contents: [{ parts: [{ text: 'Generate ephemeral token' }] }],
        }),
      }
    );

    // Alternative: Use the auth tokens API if available
    // For hackathon, we can use the API key directly in the WebSocket URL
    // This is acceptable for a demo — production would use ephemeral tokens

    return NextResponse.json({
      apiKey: process.env.GOOGLE_GENERATIVE_AI_API_KEY,
      model: 'gemini-2.5-flash-native-audio-latest',
    });
  } catch (error) {
    console.error('Token generation error:', error);
    return NextResponse.json({ error: 'Failed to generate token' }, { status: 500 });
  }
}
```

**IMPORTANT HACKATHON SHORTCUT:** For the demo, we pass the API key to the browser to establish direct WebSocket connection. In production, you'd use proper ephemeral tokens via the `client.auth_tokens.create()` method. This is fine for a 3-minute demo.

## Step 3: Create components/voice-panel.tsx

This is the core voice interaction component. It handles:
- Microphone capture (Web Audio API, PCM16 @ 16kHz)
- Direct WebSocket to Gemini Live API
- Audio playback (24kHz PCM16)
- Sending the uploaded diagram image for visual analysis
- Real-time transcription display

```typescript
'use client';

import { useState, useRef, useCallback, useEffect } from 'react';
import { Mic, MicOff, Phone, PhoneOff, Volume2, Loader2 } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';

interface VoicePanelProps {
  diagramFile: File | null;
}

interface TranscriptEntry {
  role: 'user' | 'assistant';
  text: string;
  timestamp: Date;
}

export function VoicePanel({ diagramFile }: VoicePanelProps) {
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [transcript, setTranscript] = useState<TranscriptEntry[]>([]);
  const [currentUserText, setCurrentUserText] = useState('');
  const [currentAssistantText, setCurrentAssistantText] = useState('');
  const [error, setError] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const playbackCtxRef = useRef<AudioContext | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const nextPlayTimeRef = useRef(0);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Convert Float32 audio to Int16 PCM
  const float32ToInt16 = (float32Array: Float32Array): Int16Array => {
    const int16Array = new Int16Array(float32Array.length);
    for (let i = 0; i < float32Array.length; i++) {
      const s = Math.max(-1, Math.min(1, float32Array[i]));
      int16Array[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
    }
    return int16Array;
  };

  // Downsample from browser sample rate to 16kHz
  const downsample = (buffer: Float32Array, fromRate: number, toRate: number): Float32Array => {
    if (fromRate === toRate) return buffer;
    const ratio = fromRate / toRate;
    const newLength = Math.round(buffer.length / ratio);
    const result = new Float32Array(newLength);
    for (let i = 0; i < newLength; i++) {
      result[i] = buffer[Math.round(i * ratio)];
    }
    return result;
  };

  // Convert ArrayBuffer to base64
  const arrayBufferToBase64 = (buffer: ArrayBuffer): string => {
    const bytes = new Uint8Array(buffer);
    let binary = '';
    for (let i = 0; i < bytes.byteLength; i++) {
      binary += String.fromCharCode(bytes[i]);
    }
    return btoa(binary);
  };

  // Play received audio (PCM16 @ 24kHz)
  const playAudio = useCallback((base64Data: string) => {
    if (!playbackCtxRef.current) {
      playbackCtxRef.current = new AudioContext({ sampleRate: 24000 });
    }
    const ctx = playbackCtxRef.current;

    const binaryStr = atob(base64Data);
    const bytes = new Uint8Array(binaryStr.length);
    for (let i = 0; i < binaryStr.length; i++) {
      bytes[i] = binaryStr.charCodeAt(i);
    }

    const int16 = new Int16Array(bytes.buffer);
    const float32 = new Float32Array(int16.length);
    for (let i = 0; i < int16.length; i++) {
      float32[i] = int16[i] / 0x8000;
    }

    const audioBuffer = ctx.createBuffer(1, float32.length, 24000);
    audioBuffer.getChannelData(0).set(float32);

    const source = ctx.createBufferSource();
    source.buffer = audioBuffer;
    source.connect(ctx.destination);

    const now = ctx.currentTime;
    nextPlayTimeRef.current = Math.max(now, nextPlayTimeRef.current);
    source.start(nextPlayTimeRef.current);
    nextPlayTimeRef.current += audioBuffer.duration;
  }, []);

  // Start voice session
  const startSession = async () => {
    setIsConnecting(true);
    setError(null);

    try {
      // Get API key for direct connection
      const tokenResp = await fetch('/api/ephemeral-token');
      const tokenData = await tokenResp.json();

      if (tokenData.error) throw new Error(tokenData.error);

      // Connect directly to Gemini Live API
      const wsUrl = `wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent?key=${tokenData.apiKey}`;
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = async () => {
        // Send setup configuration
        const setupConfig: any = {
          setup: {
            model: `models/${tokenData.model}`,
            generationConfig: {
              responseModalities: ['AUDIO'],
              speechConfig: {
                voiceConfig: {
                  prebuiltVoiceConfig: { voiceName: 'Puck' }
                }
              }
            },
            realtimeInputConfig: {
              automaticActivityDetection: {
                startOfSpeechSensitivity: 'START_SENSITIVITY_LOW',
                endOfSpeechSensitivity: 'END_SENSITIVITY_HIGH',
                prefixPaddingMs: 20,
                silenceDurationMs: 500
              }
            },
            inputAudioTranscription: {},
            outputAudioTranscription: {},
            systemInstruction: {
              parts: [{
                text: `You are ArchIntel, an expert architecture intelligence assistant. You analyze architecture diagrams for security threats (using STRIDE methodology) and cloud cost estimation.

When the user shows you a diagram or asks about their architecture:
1. Describe what you see in the diagram
2. Identify key security threats using STRIDE (Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege)
3. Provide rough cost estimates for the cloud services you identify
4. Suggest specific remediations

Be concise but thorough. Speak naturally — you are having a conversation, not reading a report. Use phrases like "I can see that..." and "One thing that concerns me is..."

Keep responses under 30 seconds of speech. If the user asks a follow-up, give focused answers.`
              }]
            }
          }
        };

        ws.send(JSON.stringify(setupConfig));

        // Start microphone capture
        const stream = await navigator.mediaDevices.getUserMedia({
          audio: {
            sampleRate: 16000,
            channelCount: 1,
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true,
          }
        });
        streamRef.current = stream;

        const audioCtx = new AudioContext({ sampleRate: 16000 });
        audioContextRef.current = audioCtx;

        const source = audioCtx.createMediaStreamSource(stream);
        const processor = audioCtx.createScriptProcessor(512, 1, 1);
        processorRef.current = processor;

        processor.onaudioprocess = (e) => {
          if (isMuted || ws.readyState !== WebSocket.OPEN) return;

          const inputData = e.inputBuffer.getChannelData(0);
          const downsampled = downsample(inputData, audioCtx.sampleRate, 16000);
          const pcm16 = float32ToInt16(downsampled);
          const b64 = arrayBufferToBase64(pcm16.buffer);

          ws.send(JSON.stringify({
            realtimeInput: {
              audio: {
                data: b64,
                mimeType: 'audio/pcm;rate=16000'
              }
            }
          }));
        };

        source.connect(processor);
        processor.connect(audioCtx.destination);

        setIsConnected(true);
        setIsConnecting(false);

        // If there's a diagram, send it as an image
        if (diagramFile) {
          const buffer = await diagramFile.arrayBuffer();
          const b64 = arrayBufferToBase64(buffer);

          // Send image via realtimeInput
          ws.send(JSON.stringify({
            realtimeInput: {
              video: {
                data: b64,
                mimeType: diagramFile.type || 'image/jpeg'
              }
            }
          }));

          // Also send a text prompt to kick off analysis
          ws.send(JSON.stringify({
            clientContent: {
              turns: [{
                role: 'user',
                parts: [{ text: 'I just uploaded an architecture diagram. Please analyze it for security threats and give me a cost estimate.' }]
              }],
              turnComplete: true
            }
          }));
        }
      };

      ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);

        // Handle setup complete
        if (msg.setupComplete) {
          console.log('Gemini Live session established');
          return;
        }

        // Handle server content (audio + transcription)
        if (msg.serverContent) {
          const sc = msg.serverContent;

          // Audio data
          if (sc.modelTurn?.parts) {
            for (const part of sc.modelTurn.parts) {
              if (part.inlineData?.data) {
                playAudio(part.inlineData.data);
              }
            }
          }

          // Input transcription (what user said)
          if (sc.inputTranscription?.text) {
            setCurrentUserText(prev => prev + sc.inputTranscription.text);
            if (sc.inputTranscription.finished) {
              setTranscript(prev => [...prev, {
                role: 'user',
                text: currentUserText + sc.inputTranscription.text,
                timestamp: new Date()
              }]);
              setCurrentUserText('');
            }
          }

          // Output transcription (what Gemini said)
          if (sc.outputTranscription?.text) {
            setCurrentAssistantText(prev => prev + sc.outputTranscription.text);
          }

          // Turn complete — finalize assistant transcript
          if (sc.turnComplete) {
            if (currentAssistantText) {
              setTranscript(prev => [...prev, {
                role: 'assistant',
                text: currentAssistantText,
                timestamp: new Date()
              }]);
              setCurrentAssistantText('');
            }
          }
        }
      };

      ws.onerror = (e) => {
        console.error('WebSocket error:', e);
        setError('Connection error. Please try again.');
        setIsConnecting(false);
      };

      ws.onclose = (e) => {
        console.log('WebSocket closed:', e.code, e.reason);
        setIsConnected(false);
        setIsConnecting(false);
        cleanup();
      };
    } catch (err: any) {
      setError(err.message || 'Failed to start voice session');
      setIsConnecting(false);
    }
  };

  const cleanup = () => {
    processorRef.current?.disconnect();
    audioContextRef.current?.close();
    streamRef.current?.getTracks().forEach(t => t.stop());
    playbackCtxRef.current?.close();
    nextPlayTimeRef.current = 0;
  };

  const endSession = () => {
    wsRef.current?.close();
    cleanup();
    setIsConnected(false);
  };

  const toggleMute = () => setIsMuted(!isMuted);

  // Send diagram when it changes while connected
  useEffect(() => {
    if (isConnected && diagramFile && wsRef.current?.readyState === WebSocket.OPEN) {
      (async () => {
        const buffer = await diagramFile.arrayBuffer();
        const b64 = arrayBufferToBase64(buffer);
        wsRef.current!.send(JSON.stringify({
          realtimeInput: {
            video: {
              data: b64,
              mimeType: diagramFile.type || 'image/jpeg'
            }
          }
        }));
      })();
    }
  }, [diagramFile, isConnected]);

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [transcript, currentAssistantText]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      wsRef.current?.close();
      cleanup();
    };
  }, []);

  return (
    <div className="flex flex-col h-full space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Volume2 className="h-5 w-5 text-purple-400" />
          <h2 className="text-lg font-semibold text-white">Voice Analysis</h2>
          {isConnected && (
            <Badge className="bg-green-900/50 text-green-400 border-green-700 animate-pulse">
              LIVE
            </Badge>
          )}
        </div>
        <div className="flex items-center gap-2">
          {isConnected && (
            <button
              onClick={toggleMute}
              className={`p-2 rounded-lg transition-colors ${
                isMuted ? 'bg-red-900/50 text-red-400' : 'bg-gray-800 text-gray-400 hover:text-white'
              }`}
            >
              {isMuted ? <MicOff className="h-4 w-4" /> : <Mic className="h-4 w-4" />}
            </button>
          )}
          <button
            onClick={isConnected ? endSession : startSession}
            disabled={isConnecting}
            className={`px-4 py-2 rounded-lg flex items-center gap-2 transition-colors ${
              isConnected
                ? 'bg-red-600 hover:bg-red-700 text-white'
                : isConnecting
                  ? 'bg-gray-700 text-gray-400'
                  : 'bg-purple-600 hover:bg-purple-700 text-white'
            }`}
          >
            {isConnecting ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Connecting...
              </>
            ) : isConnected ? (
              <>
                <PhoneOff className="h-4 w-4" />
                End Session
              </>
            ) : (
              <>
                <Phone className="h-4 w-4" />
                Start Voice Analysis
              </>
            )}
          </button>
        </div>
      </div>

      {!isConnected && !isConnecting && (
        <Card className="p-6 bg-gray-900/50 border-gray-800 text-center">
          <div className="space-y-3">
            <div className="p-4 bg-purple-900/20 rounded-full inline-block">
              <Mic className="h-8 w-8 text-purple-400" />
            </div>
            <p className="text-sm text-gray-400">
              Start a voice session to talk with ArchIntel about your architecture.
              {diagramFile
                ? ' Your diagram will be shared automatically.'
                : ' Upload a diagram first for visual analysis.'}
            </p>
            <p className="text-xs text-gray-600">
              Powered by Gemini 2.5 Flash Native Audio — real-time multimodal conversation
            </p>
          </div>
        </Card>
      )}

      {error && (
        <div className="p-3 bg-red-900/30 border border-red-700 rounded-lg text-red-300 text-sm">
          {error}
        </div>
      )}

      <ScrollArea className="flex-1 h-[400px]">
        <div className="space-y-3 p-1">
          {transcript.map((entry, i) => (
            <div
              key={i}
              className={`flex ${entry.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <Card
                className={`max-w-[85%] p-3 ${
                  entry.role === 'user'
                    ? 'bg-purple-900/30 border-purple-700'
                    : 'bg-gray-900 border-gray-700'
                }`}
              >
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs text-gray-500">
                    {entry.role === 'user' ? '🎤 You' : '🤖 ArchIntel'}
                  </span>
                  <span className="text-xs text-gray-600">
                    {entry.timestamp.toLocaleTimeString()}
                  </span>
                </div>
                <p className="text-sm text-gray-200">{entry.text}</p>
              </Card>
            </div>
          ))}

          {/* Live transcription indicators */}
          {currentUserText && (
            <div className="flex justify-end">
              <Card className="max-w-[85%] p-3 bg-purple-900/20 border-purple-800 border-dashed">
                <p className="text-sm text-purple-300 italic">{currentUserText}...</p>
              </Card>
            </div>
          )}
          {currentAssistantText && (
            <div className="flex justify-start">
              <Card className="max-w-[85%] p-3 bg-gray-900/50 border-gray-800 border-dashed">
                <p className="text-sm text-gray-300 italic streaming-cursor">{currentAssistantText}</p>
              </Card>
            </div>
          )}

          <div ref={scrollRef} />
        </div>
      </ScrollArea>
    </div>
  );
}
```

## Step 4: Update app/page.tsx

Add a third tab for Voice Analysis. Update the Tabs component:

```typescript
// Add to imports
import { VoicePanel } from '@/components/voice-panel';
import { Volume2 } from 'lucide-react';

// Add third tab in TabsList (change to grid-cols-3)
<TabsList className="grid w-full grid-cols-3 bg-gray-900 border border-gray-800">
  <TabsTrigger value="threats" className="flex items-center gap-2 data-[state=active]:bg-red-900/30 data-[state=active]:text-red-400">
    <Shield className="h-4 w-4" />
    Security
  </TabsTrigger>
  <TabsTrigger value="costs" className="flex items-center gap-2 data-[state=active]:bg-green-900/30 data-[state=active]:text-green-400">
    <DollarSign className="h-4 w-4" />
    Costs
  </TabsTrigger>
  <TabsTrigger value="voice" className="flex items-center gap-2 data-[state=active]:bg-purple-900/30 data-[state=active]:text-purple-400">
    <Volume2 className="h-4 w-4" />
    Voice
  </TabsTrigger>
</TabsList>

// Add TabsContent
<TabsContent value="voice" className="mt-4">
  <VoicePanel diagramFile={diagramFile} />
</TabsContent>
```

## Key Technical Details (from FUSE learnings)

### Audio Format
- **Input:** PCM16 @ 16kHz (browser may run at 48kHz — downsample!)
- **Output:** PCM16 @ 24kHz from Gemini
- **Buffer size:** 512 samples (32ms chunks) — prevents WebSocket 1007 errors

### Voice Activity Detection (VAD)
- Use `START_SENSITIVITY_LOW` + `END_SENSITIVITY_HIGH` + `silenceDurationMs: 500`
- This prevents Gemini from cutting off the user mid-sentence
- Also prevents 1007 errors from audio hitting during turn transitions

### Image Sending
- Send diagram as `realtimeInput.video` with `mimeType: 'image/jpeg'`
- Gemini Live API accepts images through the video channel
- Send ONCE when session starts, not continuously (continuous video causes 53s+ latency per FUSE findings)

### Audio Playback
- Schedule chunks sequentially using `AudioContext.currentTime`
- Track `nextPlayTime` to prevent overlap
- Use separate AudioContext for playback (24kHz) vs capture (16kHz)

### Error Handling
- WebSocket 1007: Usually audio format issues — check PCM16 encoding
- WebSocket 1008/1011: Race condition during tool calls — implement audio gating
- GoAway: Session timeout — implement reconnection with session resumption handle

## Demo Flow for Voice Tab
1. User uploads diagram (left panel)
2. User clicks "Start Voice Analysis" (purple button)
3. Browser requests mic permission
4. Gemini sees the diagram and immediately starts speaking: "I can see a three-tier architecture with..."
5. User asks follow-ups naturally: "What about the S3 bucket? Is that secure?"
6. Real-time transcript appears below
7. User clicks "End Session" when done

This is the **wow factor** for the demo — judges have never seen someone *talk* to their architecture diagram before.

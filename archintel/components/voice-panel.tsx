'use client';

import { useState, useRef, useCallback, useEffect } from 'react';
import { Mic, MicOff, Phone, PhoneOff, Volume2, Loader2, Shield, DollarSign, Check, AlertTriangle } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { formatThreatSummaryForVoice, formatCostSummaryForVoice } from '@/lib/format-voice-context';
import type { ThreatResults } from '@/lib/parse-threat-stream';
import type { PipelineStatus, CostResults } from '@/lib/pipeline-types';

interface VoicePanelProps {
  diagramFile: File | null;
  onPipelineTrigger?: (file: File) => void;
  pipelineStatus?: { threat: PipelineStatus; cost: PipelineStatus };
  threatResults?: ThreatResults | null;
  costResults?: CostResults | null;
}

interface TranscriptEntry {
  role: 'user' | 'assistant';
  text: string;
  timestamp: Date;
}

function arrayBufferToBase64(buffer: ArrayBuffer | ArrayBufferLike): string {
  const bytes = new Uint8Array(buffer);
  let binary = '';
  for (let i = 0; i < bytes.byteLength; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}

function float32ToInt16(float32Array: Float32Array): Int16Array {
  const int16Array = new Int16Array(float32Array.length);
  for (let i = 0; i < float32Array.length; i++) {
    const s = Math.max(-1, Math.min(1, float32Array[i]));
    int16Array[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
  }
  return int16Array;
}

function downsample(buffer: Float32Array, fromRate: number, toRate: number): Float32Array {
  if (fromRate === toRate) return buffer;
  const ratio = fromRate / toRate;
  const newLength = Math.round(buffer.length / ratio);
  const result = new Float32Array(newLength);
  for (let i = 0; i < newLength; i++) {
    result[i] = buffer[Math.round(i * ratio)];
  }
  return result;
}

function PipelineStatusPill({ label, status, icon: Icon }: { label: string; status: PipelineStatus; icon: React.ComponentType<{ className?: string }> }) {
  return (
    <div className="flex items-center gap-1.5">
      <Icon className="h-3 w-3" />
      <span>{label}</span>
      {status === 'running' && <Loader2 className="h-3 w-3 animate-spin text-blue-400" />}
      {status === 'complete' && <Check className="h-3 w-3 text-green-400" />}
      {status === 'error' && <AlertTriangle className="h-3 w-3 text-yellow-400" />}
    </div>
  );
}

export function VoicePanel({ diagramFile, onPipelineTrigger, pipelineStatus, threatResults, costResults }: VoicePanelProps) {
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [transcript, setTranscript] = useState<TranscriptEntry[]>([]);
  const [currentAssistantText, setCurrentAssistantText] = useState('');
  const [error, setError] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const playbackCtxRef = useRef<AudioContext | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const nextPlayTimeRef = useRef(0);
  const scrollRef = useRef<HTMLDivElement>(null);
  const isMutedRef = useRef(false);
  const assistantTextRef = useRef('');
  const threatInjectedRef = useRef(false);
  const costInjectedRef = useRef(false);

  useEffect(() => {
    isMutedRef.current = isMuted;
  }, [isMuted]);

  // Inject threat results into voice context when they arrive
  useEffect(() => {
    if (threatResults && !threatInjectedRef.current && wsRef.current?.readyState === WebSocket.OPEN) {
      const summary = formatThreatSummaryForVoice(threatResults);
      wsRef.current.send(JSON.stringify({
        clientContent: {
          turns: [{
            role: 'user',
            parts: [{ text: summary }]
          }],
          turnComplete: true
        }
      }));
      threatInjectedRef.current = true;
    }
  }, [threatResults]);

  // Inject cost results into voice context when they arrive
  useEffect(() => {
    if (costResults && !costInjectedRef.current && wsRef.current?.readyState === WebSocket.OPEN) {
      const summary = formatCostSummaryForVoice(costResults);
      wsRef.current.send(JSON.stringify({
        clientContent: {
          turns: [{
            role: 'user',
            parts: [{ text: summary }]
          }],
          turnComplete: true
        }
      }));
      costInjectedRef.current = true;
    }
  }, [costResults]);

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

  const cleanup = useCallback(() => {
    processorRef.current?.disconnect();
    audioContextRef.current?.close().catch(() => {});
    streamRef.current?.getTracks().forEach(t => t.stop());
    playbackCtxRef.current?.close().catch(() => {});
    audioContextRef.current = null;
    playbackCtxRef.current = null;
    processorRef.current = null;
    streamRef.current = null;
    nextPlayTimeRef.current = 0;
  }, []);

  const startSession = async () => {
    setIsConnecting(true);
    setError(null);
    assistantTextRef.current = '';
    threatInjectedRef.current = false;
    costInjectedRef.current = false;

    try {
      const tokenResp = await fetch('/api/ephemeral-token');
      const tokenData = await tokenResp.json();
      if (tokenData.error) throw new Error(tokenData.error);

      const wsUrl = `wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent?key=${tokenData.apiKey}`;
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        const setupConfig = {
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
2. Give a brief initial security and cost overview based on what you see

IMPORTANT: You will receive structured analysis data marked with [SECURITY ANALYSIS COMPLETE] and [COST ANALYSIS COMPLETE] during the conversation. When you receive this data:
- Use it to answer specific questions about threats, costs, and remediations
- Reference specific threat names, severities, and Terraform filenames from the data
- Reference specific cost figures and service breakdowns from the data
- When asked about Terraform, refer the user to the Security tab where files are displayed

Be concise but thorough. Speak naturally. Keep responses under 30 seconds of speech.
When citing specific numbers or findings, say "according to our analysis" to indicate the data is from the automated pipeline.`
              }]
            }
          }
        };
        ws.send(JSON.stringify(setupConfig));
      };

      ws.onmessage = async (event) => {
        const msg = JSON.parse(event.data);

        if (msg.setupComplete) {
          console.log('Gemini Live session established');
          setIsConnected(true);
          setIsConnecting(false);

          // Trigger automated analysis pipeline
          if (diagramFile && onPipelineTrigger) {
            onPipelineTrigger(diagramFile);
          }

          // Start microphone
          try {
            const stream = await navigator.mediaDevices.getUserMedia({
              audio: {
                channelCount: 1,
                echoCancellation: true,
                noiseSuppression: true,
                autoGainControl: true,
              }
            });
            streamRef.current = stream;

            const audioCtx = new AudioContext();
            audioContextRef.current = audioCtx;

            const source = audioCtx.createMediaStreamSource(stream);
            const processor = audioCtx.createScriptProcessor(512, 1, 1);
            processorRef.current = processor;

            processor.onaudioprocess = (e) => {
              if (isMutedRef.current || ws.readyState !== WebSocket.OPEN) return;
              const inputData = e.inputBuffer.getChannelData(0);
              const downsampled = downsample(inputData, audioCtx.sampleRate, 16000);
              const pcm16 = float32ToInt16(downsampled);
              const b64 = arrayBufferToBase64(pcm16.buffer);

              ws.send(JSON.stringify({
                realtimeInput: {
                  audio: { data: b64, mimeType: 'audio/pcm;rate=16000' }
                }
              }));
            };

            source.connect(processor);
            processor.connect(audioCtx.destination);
          } catch (micErr) {
            console.error('Microphone error:', micErr);
            setError('Could not access microphone. Please allow microphone permissions.');
          }

          // Send diagram if available
          if (diagramFile) {
            const buffer = await diagramFile.arrayBuffer();
            const b64 = arrayBufferToBase64(buffer);
            ws.send(JSON.stringify({
              realtimeInput: {
                video: { data: b64, mimeType: diagramFile.type || 'image/jpeg' }
              }
            }));
            ws.send(JSON.stringify({
              clientContent: {
                turns: [{
                  role: 'user',
                  parts: [{ text: 'I just uploaded an architecture diagram. Please analyze it for security threats and give me a brief overview. I have also kicked off automated security and cost analyses that will provide detailed findings shortly.' }]
                }],
                turnComplete: true
              }
            }));
          }

          return;
        }

        if (msg.serverContent) {
          const sc = msg.serverContent;

          if (sc.modelTurn?.parts) {
            for (const part of sc.modelTurn.parts) {
              if (part.inlineData?.data) {
                playAudio(part.inlineData.data);
              }
            }
          }

          if (sc.inputTranscription?.text) {
            const text = sc.inputTranscription.text.trim();
            if (text) {
              setTranscript(prev => [...prev, {
                role: 'user',
                text,
                timestamp: new Date()
              }]);
            }
          }

          if (sc.outputTranscription?.text) {
            assistantTextRef.current += sc.outputTranscription.text;
            setCurrentAssistantText(assistantTextRef.current);
          }

          if (sc.turnComplete) {
            if (assistantTextRef.current.trim()) {
              const finalText = assistantTextRef.current.trim();
              setTranscript(prev => [...prev, {
                role: 'assistant',
                text: finalText,
                timestamp: new Date()
              }]);
            }
            assistantTextRef.current = '';
            setCurrentAssistantText('');
          }
        }
      };

      ws.onerror = () => {
        setError('Connection error. Please try again.');
        setIsConnecting(false);
      };

      ws.onclose = (e) => {
        console.log('WebSocket closed:', e.code, e.reason);
        if (e.code !== 1000 && e.code !== 1005) {
          setError(`Voice session ended (code: ${e.code}). Please try again.`);
        }
        setIsConnected(false);
        setIsConnecting(false);
        cleanup();
      };
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to start voice session';
      setError(message);
      setIsConnecting(false);
    }
  };

  const endSession = () => {
    wsRef.current?.close();
    cleanup();
    setIsConnected(false);
  };

  const toggleMute = () => setIsMuted(!isMuted);

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [transcript, currentAssistantText]);

  useEffect(() => {
    return () => {
      wsRef.current?.close();
      cleanup();
    };
  }, [cleanup]);

  if (!diagramFile && !isConnected) {
    return (
      <div className="flex flex-col items-center justify-center h-[400px] text-muted-foreground border border-border rounded-xl bg-card/30">
        <Volume2 className="h-12 w-12 mb-4 opacity-30" />
        <p className="text-sm">Upload a diagram to start a voice conversation</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Volume2 className="h-5 w-5 text-purple-400" />
          <h2 className="text-lg font-semibold">Voice Analysis</h2>
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
                isMuted ? 'bg-red-900/50 text-red-400' : 'bg-secondary text-muted-foreground hover:text-foreground'
              }`}
            >
              {isMuted ? <MicOff className="h-4 w-4" /> : <Mic className="h-4 w-4" />}
            </button>
          )}
          <button
            onClick={isConnected ? endSession : startSession}
            disabled={isConnecting}
            className={`px-4 py-2 rounded-lg flex items-center gap-2 transition-colors text-sm font-medium ${
              isConnected
                ? 'bg-red-600 hover:bg-red-700 text-white'
                : isConnecting
                  ? 'bg-secondary text-muted-foreground'
                  : 'bg-purple-600 hover:bg-purple-700 text-white'
            }`}
          >
            {isConnecting ? (
              <><Loader2 className="h-4 w-4 animate-spin" />Connecting...</>
            ) : isConnected ? (
              <><PhoneOff className="h-4 w-4" />End Session</>
            ) : (
              <><Phone className="h-4 w-4" />Start Voice Analysis</>
            )}
          </button>
        </div>
      </div>

      {/* Pipeline Status Bar */}
      {pipelineStatus && (pipelineStatus.threat !== 'idle' || pipelineStatus.cost !== 'idle') && (
        <Card className="p-3 bg-card/50 border-border">
          <div className="flex items-center gap-6 text-xs text-muted-foreground">
            <span className="font-medium">Auto-analyzing:</span>
            <PipelineStatusPill label="Security" status={pipelineStatus.threat} icon={Shield} />
            <PipelineStatusPill label="Costs" status={pipelineStatus.cost} icon={DollarSign} />
          </div>
        </Card>
      )}

      {!isConnected && !isConnecting && (
        <Card className="p-6 bg-card/50 border-border text-center">
          <div className="space-y-3">
            <div className="p-4 bg-purple-900/20 rounded-full inline-block">
              <Mic className="h-8 w-8 text-purple-400" />
            </div>
            <p className="text-sm text-muted-foreground">
              Start a voice session to talk with ArchIntel about your architecture.
              Security and cost analyses will run automatically.
            </p>
            <p className="text-xs text-muted-foreground/60">
              Powered by Gemini 2.5 Flash Native Audio
            </p>
          </div>
        </Card>
      )}

      {error && (
        <div className="p-3 bg-red-900/30 border border-red-800 rounded-lg text-red-300 text-sm">
          {error}
        </div>
      )}

      {(transcript.length > 0 || currentAssistantText) && (
        <ScrollArea className="h-[400px]">
          <div className="space-y-3 p-1">
            {transcript.map((entry, i) => (
              <div
                key={i}
                className={`flex ${entry.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <Card
                  className={`max-w-[85%] p-3 ${
                    entry.role === 'user'
                      ? 'bg-purple-900/30 border-purple-800'
                      : 'bg-card border-border'
                  }`}
                >
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs text-muted-foreground">
                      {entry.role === 'user' ? 'You' : 'ArchIntel'}
                    </span>
                    <span className="text-xs text-muted-foreground/50">
                      {entry.timestamp.toLocaleTimeString()}
                    </span>
                  </div>
                  <p className="text-sm">{entry.text}</p>
                </Card>
              </div>
            ))}

            {currentAssistantText && (
              <div className="flex justify-start">
                <Card className="max-w-[85%] p-3 bg-card/50 border-border border-dashed">
                  <p className="text-sm text-muted-foreground streaming-cursor">{currentAssistantText}</p>
                </Card>
              </div>
            )}

            <div ref={scrollRef} />
          </div>
        </ScrollArea>
      )}
    </div>
  );
}

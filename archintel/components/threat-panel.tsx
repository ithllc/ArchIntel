'use client';

import { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { Shield, AlertTriangle, FileCode, Loader2, Copy, Check } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import type { ThreatResults } from '@/lib/parse-threat-stream';
import type { PipelineStatus } from '@/lib/pipeline-types';

interface TerraformFile {
  filename: string;
  content: string;
  threatName: string;
  severity: string;
}

interface ThreatPanelProps {
  diagramFile: File | null;
  pipelineStatus?: PipelineStatus;
  pipelineResults?: ThreatResults | null;
}

export function ThreatPanel({ diagramFile, pipelineStatus, pipelineResults }: ThreatPanelProps) {
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [streamedText, setStreamedText] = useState('');
  const [terraformFiles, setTerraformFiles] = useState<TerraformFile[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);
  const [isFromPipeline, setIsFromPipeline] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [streamedText]);

  // Auto-populate from pipeline results
  useEffect(() => {
    if (pipelineResults && !isAnalyzing) {
      setStreamedText(pipelineResults.text);
      setTerraformFiles(pipelineResults.terraformFiles);
      setIsFromPipeline(true);
    }
  }, [pipelineResults, isAnalyzing]);

  const analyze = async () => {
    if (!diagramFile) return;

    setIsAnalyzing(true);
    setStreamedText('');
    setTerraformFiles([]);
    setError(null);
    setIsFromPipeline(false);

    try {
      const formData = new FormData();
      formData.append('diagram', diagramFile);

      const response = await fetch('/api/threat-model', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) throw new Error('Analysis failed');

      const reader = response.body?.getReader();
      if (!reader) throw new Error('No response body');

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          // UI Message Stream format: "data: {json}"
          if (!line.startsWith('data: ')) continue;
          const jsonStr = line.slice(6);
          if (!jsonStr.trim()) continue;

          try {
            const evt = JSON.parse(jsonStr);

            // Text delta — append to streamed text
            if (evt.type === 'text' && evt.text) {
              setStreamedText(prev => prev + evt.text);
            }

            // Tool call — extract Terraform args
            if (evt.type === 'tool-call' && evt.toolName === 'generateTerraform' && evt.args) {
              const args = evt.args;
              setTerraformFiles(prev => {
                if (prev.some(f => f.filename === args.filename)) return prev;
                return [...prev, {
                  filename: args.filename,
                  content: args.content,
                  threatName: args.threatName,
                  severity: args.severity,
                }];
              });
            }

            // Tool result — also extract Terraform if present
            if (evt.type === 'tool-result' && evt.result?.filename) {
              setTerraformFiles(prev => {
                if (prev.some(f => f.filename === evt.result.filename)) return prev;
                return [...prev, {
                  filename: evt.result.filename,
                  content: evt.result.content || '',
                  threatName: evt.result.threatName || '',
                  severity: evt.result.severity || 'HIGH',
                }];
              });
            }
          } catch {
            // skip malformed JSON
          }
        }
      }
    } catch {
      setError('Failed to analyze diagram. Please try again.');
    } finally {
      setIsAnalyzing(false);
    }
  };

  const copyToClipboard = (content: string, index: number) => {
    navigator.clipboard.writeText(content);
    setCopiedIndex(index);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  if (!diagramFile) {
    return (
      <div className="flex flex-col items-center justify-center h-[400px] text-muted-foreground border border-border rounded-xl bg-card/30">
        <Shield className="h-12 w-12 mb-4 opacity-30" />
        <p className="text-sm">Upload a diagram to run STRIDE threat analysis</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Shield className="h-5 w-5 text-red-400" />
          <h2 className="text-lg font-semibold">STRIDE Threat Analysis</h2>
          {isFromPipeline && !isAnalyzing && streamedText && (
            <Badge className="bg-purple-900/30 text-purple-400 border-purple-700 text-xs">
              Auto-analyzed via Voice
            </Badge>
          )}
          {pipelineStatus === 'running' && !isAnalyzing && !streamedText && (
            <Badge className="bg-blue-900/30 text-blue-400 border-blue-700 text-xs animate-pulse">
              <Loader2 className="h-3 w-3 animate-spin mr-1" />
              Auto-analyzing...
            </Badge>
          )}
        </div>
        <button
          onClick={analyze}
          disabled={!diagramFile || isAnalyzing}
          className="px-4 py-2 bg-red-600 hover:bg-red-700 disabled:bg-secondary disabled:text-muted-foreground text-white rounded-lg flex items-center gap-2 transition-colors text-sm font-medium"
        >
          {isAnalyzing ? (
            <><Loader2 className="h-4 w-4 animate-spin" />Analyzing...</>
          ) : (
            <><AlertTriangle className="h-4 w-4" />{streamedText ? 'Re-run Analysis' : 'Run Analysis'}</>
          )}
        </button>
      </div>

      {error && (
        <div className="p-3 bg-red-900/30 border border-red-800 rounded-lg text-red-300 text-sm">
          {error}
        </div>
      )}

      {streamedText && (
        <ScrollArea className="h-[500px]">
          <Card className="p-5 bg-card border-border">
            <div className="prose prose-invert prose-sm max-w-none prose-headings:text-foreground prose-p:text-muted-foreground prose-strong:text-foreground prose-li:text-muted-foreground">
              <ReactMarkdown>{streamedText}</ReactMarkdown>
            </div>
            {isAnalyzing && <span className="streaming-cursor" />}
            <div ref={scrollRef} />
          </Card>
        </ScrollArea>
      )}

      {terraformFiles.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <FileCode className="h-5 w-5 text-green-400" />
            <h3 className="font-semibold">Generated Terraform Policies</h3>
            <Badge variant="outline" className="text-green-400 border-green-800">
              {terraformFiles.length} {terraformFiles.length === 1 ? 'file' : 'files'}
            </Badge>
          </div>
          {terraformFiles.map((tf, i) => (
            <Card key={i} className="bg-card border-border overflow-hidden">
              <div className="px-3 py-2 bg-secondary/50 border-b border-border flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Badge variant="outline" className="text-green-400 border-green-800 text-xs">
                    {tf.filename}
                  </Badge>
                  <Badge
                    variant="outline"
                    className={`text-xs ${
                      tf.severity === 'CRITICAL' ? 'text-red-400 border-red-800' :
                      tf.severity === 'HIGH' ? 'text-orange-400 border-orange-800' :
                      'text-yellow-400 border-yellow-800'
                    }`}
                  >
                    {tf.severity}
                  </Badge>
                  <span className="text-xs text-muted-foreground">{tf.threatName}</span>
                </div>
                <button
                  onClick={() => copyToClipboard(tf.content, i)}
                  className="p-1 hover:bg-secondary rounded transition-colors"
                >
                  {copiedIndex === i ? (
                    <Check className="h-3.5 w-3.5 text-green-400" />
                  ) : (
                    <Copy className="h-3.5 w-3.5 text-muted-foreground" />
                  )}
                </button>
              </div>
              <SyntaxHighlighter
                language="hcl"
                style={oneDark}
                customStyle={{ margin: 0, background: 'transparent', fontSize: '0.8rem' }}
              >
                {tf.content}
              </SyntaxHighlighter>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

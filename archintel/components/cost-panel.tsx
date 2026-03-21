'use client';

import { useChat } from '@ai-sdk/react';
import { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import { DollarSign, Send, Loader2, TrendingDown } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';

interface CostPanelProps {
  diagramFile: File | null;
}

export function CostPanel({ diagramFile }: CostPanelProps) {
  const [hasStarted, setHasStarted] = useState(false);
  const [inputText, setInputText] = useState('');
  const scrollRef = useRef<HTMLDivElement>(null);

  const { messages, sendMessage, status } = useChat();

  const isLoading = status === 'streaming' || status === 'submitted';

  const startAnalysis = async () => {
    if (!diagramFile) return;
    setHasStarted(true);

    const buffer = await diagramFile.arrayBuffer();
    const base64 = btoa(
      new Uint8Array(buffer).reduce((data, byte) => data + String.fromCharCode(byte), '')
    );

    sendMessage({
      text: 'Analyze this architecture diagram and identify all cloud services. Then ask me about our expected traffic so you can estimate costs.',
      files: [{
        type: 'file' as const,
        mediaType: diagramFile.type || 'image/png',
        url: `data:${diagramFile.type || 'image/png'};base64,${base64}`,
      }],
    });
  };

  const handleSend = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim() || isLoading) return;
    sendMessage({ text: inputText });
    setInputText('');
  };

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  if (!diagramFile) {
    return (
      <div className="flex flex-col items-center justify-center h-[400px] text-muted-foreground border border-border rounded-xl bg-card/30">
        <DollarSign className="h-12 w-12 mb-4 opacity-30" />
        <p className="text-sm">Upload a diagram to estimate cloud costs</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <DollarSign className="h-5 w-5 text-green-400" />
          <h2 className="text-lg font-semibold">Cost Estimation</h2>
        </div>
        {!hasStarted && (
          <button
            onClick={startAnalysis}
            disabled={!diagramFile}
            className="px-4 py-2 bg-green-600 hover:bg-green-700 disabled:bg-secondary disabled:text-muted-foreground text-white rounded-lg flex items-center gap-2 transition-colors text-sm font-medium"
          >
            <TrendingDown className="h-4 w-4" />
            Estimate Costs
          </button>
        )}
      </div>

      <ScrollArea className="h-[400px]">
        <div className="space-y-4 p-1">
          {messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <Card
                className={`max-w-[85%] p-3 ${
                  message.role === 'user'
                    ? 'bg-green-900/30 border-green-800'
                    : 'bg-card border-border'
                }`}
              >
                <div className="prose prose-invert prose-sm max-w-none prose-headings:text-foreground prose-p:text-muted-foreground prose-strong:text-foreground prose-li:text-muted-foreground prose-td:text-muted-foreground prose-th:text-foreground">
                  <ReactMarkdown>
                    {message.parts
                      ?.filter((p): p is { type: 'text'; text: string } => p.type === 'text')
                      .map(p => p.text)
                      .join('') || ''}
                  </ReactMarkdown>
                </div>
              </Card>
            </div>
          ))}
          {isLoading && (
            <div className="flex items-center gap-2 text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              <span className="text-sm">Calculating...</span>
            </div>
          )}
          <div ref={scrollRef} />
        </div>
      </ScrollArea>

      {hasStarted && (
        <form onSubmit={handleSend} className="flex gap-2">
          <input
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            placeholder="e.g., We expect 1M requests/month with 500GB storage..."
            className="flex-1 px-3 py-2 bg-secondary border border-border rounded-lg text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-green-500"
          />
          <button
            type="submit"
            disabled={isLoading || !inputText.trim()}
            className="px-4 py-2 bg-green-600 hover:bg-green-700 disabled:bg-secondary disabled:text-muted-foreground text-white rounded-lg transition-colors"
          >
            <Send className="h-4 w-4" />
          </button>
        </form>
      )}
    </div>
  );
}

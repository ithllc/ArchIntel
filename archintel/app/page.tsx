'use client';

import { useState } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { UploadZone } from '@/components/upload-zone';
import { ThreatPanel } from '@/components/threat-panel';
import { CostPanel } from '@/components/cost-panel';
import { VoicePanel } from '@/components/voice-panel';
import { Shield, DollarSign, Volume2, Zap } from 'lucide-react';

export default function Home() {
  const [diagramFile, setDiagramFile] = useState<File | null>(null);

  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="sticky top-0 z-50 border-b border-border bg-background/80 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-gradient-to-br from-red-500 to-green-500 rounded-lg">
              <Zap className="h-5 w-5 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight">ArchIntel</h1>
              <p className="text-xs text-muted-foreground">Architecture Intelligence Platform</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground/60">Powered by</span>
            <span className="text-xs font-medium text-muted-foreground">Gemini 2.5 Flash + 1.5 Pro</span>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Left: Upload Zone */}
          <div className="lg:col-span-1 space-y-4">
            <h2 className="text-sm font-medium text-muted-foreground uppercase tracking-wider">
              Architecture Diagram
            </h2>
            <UploadZone onFileSelect={setDiagramFile} currentFile={diagramFile} />

            {diagramFile && (
              <div className="p-3 bg-card/50 rounded-lg border border-border">
                <p className="text-xs text-muted-foreground">
                  Select a tab to analyze security threats, estimate costs, or start a voice conversation.
                </p>
              </div>
            )}
          </div>

          {/* Right: Analysis Tabs */}
          <div className="lg:col-span-2">
            <Tabs defaultValue="voice" className="w-full">
              <TabsList className="grid w-full grid-cols-3 bg-card border border-border">
                <TabsTrigger
                  value="voice"
                  className="flex items-center gap-2 data-[state=active]:bg-purple-900/30 data-[state=active]:text-purple-400"
                >
                  <Volume2 className="h-4 w-4" />
                  Voice
                </TabsTrigger>
                <TabsTrigger
                  value="threats"
                  className="flex items-center gap-2 data-[state=active]:bg-red-900/30 data-[state=active]:text-red-400"
                >
                  <Shield className="h-4 w-4" />
                  Security
                </TabsTrigger>
                <TabsTrigger
                  value="costs"
                  className="flex items-center gap-2 data-[state=active]:bg-green-900/30 data-[state=active]:text-green-400"
                >
                  <DollarSign className="h-4 w-4" />
                  Costs
                </TabsTrigger>
              </TabsList>
              <TabsContent value="voice" className="mt-4">
                <VoicePanel diagramFile={diagramFile} />
              </TabsContent>
              <TabsContent value="threats" className="mt-4">
                <ThreatPanel diagramFile={diagramFile} />
              </TabsContent>
              <TabsContent value="costs" className="mt-4">
                <CostPanel diagramFile={diagramFile} />
              </TabsContent>
            </Tabs>
          </div>
        </div>
      </main>
    </div>
  );
}

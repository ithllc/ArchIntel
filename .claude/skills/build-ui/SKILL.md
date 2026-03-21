---
name: build-ui
description: Build the ArchIntel polished dark-mode UI — main layout, drag-and-drop upload zone, tabbed output panels, and streaming indicators. Enterprise DevTools aesthetic.
user_invocable: true
---

# Build ArchIntel UI

You are building the main UI shell for ArchIntel. This must look like a polished enterprise DevTools SaaS product. Dark mode. Clean. Reactive. The live demo is 45% of judging — the UI must be impressive.

## Prerequisites
- Project scaffolded with Shadcn UI components installed
- ThreatPanel and CostPanel components exist (or will be built after)

## File 1: app/globals.css

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  --background: 0 0% 3.9%;
  --foreground: 0 0% 98%;
  --card: 0 0% 6%;
  --card-foreground: 0 0% 98%;
  --primary: 0 0% 98%;
  --primary-foreground: 0 0% 9%;
  --secondary: 0 0% 14.9%;
  --secondary-foreground: 0 0% 98%;
  --muted: 0 0% 14.9%;
  --muted-foreground: 0 0% 63.9%;
  --accent: 0 0% 14.9%;
  --accent-foreground: 0 0% 98%;
  --destructive: 0 62.8% 30.6%;
  --destructive-foreground: 0 0% 98%;
  --border: 0 0% 14.9%;
  --input: 0 0% 14.9%;
  --ring: 0 0% 83.1%;
}

body {
  background-color: hsl(var(--background));
  color: hsl(var(--foreground));
  font-family: 'Inter', system-ui, sans-serif;
}

/* Streaming cursor effect */
@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}
.streaming-cursor::after {
  content: '▊';
  animation: blink 1s infinite;
  color: #10b981;
}

/* Custom scrollbar */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: hsl(var(--background)); }
::-webkit-scrollbar-thumb { background: hsl(var(--border)); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: hsl(var(--muted-foreground)); }
```

## File 2: app/layout.tsx

```typescript
import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'ArchIntel — Architecture Intelligence',
  description: 'Upload your architecture. Understand its risks and costs in seconds.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.className} min-h-screen bg-black`}>
        {children}
      </body>
    </html>
  );
}
```

## File 3: components/upload-zone.tsx

```typescript
'use client';

import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, Image, X, FileImage } from 'lucide-react';

interface UploadZoneProps {
  onFileSelect: (file: File) => void;
  currentFile: File | null;
}

export function UploadZone({ onFileSelect, currentFile }: UploadZoneProps) {
  const [preview, setPreview] = useState<string | null>(null);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const file = acceptedFiles[0];
    if (file) {
      onFileSelect(file);
      const reader = new FileReader();
      reader.onload = () => setPreview(reader.result as string);
      reader.readAsDataURL(file);
    }
  }, [onFileSelect]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'image/*': ['.png', '.jpg', '.jpeg', '.webp', '.svg'] },
    maxFiles: 1,
    maxSize: 10 * 1024 * 1024, // 10MB
  });

  const clearFile = () => {
    setPreview(null);
    onFileSelect(null as any);
  };

  if (preview && currentFile) {
    return (
      <div className="relative group">
        <div className="rounded-xl border border-gray-700 bg-gray-900/50 p-2 overflow-hidden">
          <div className="flex items-center justify-between mb-2 px-2">
            <div className="flex items-center gap-2 text-sm text-gray-400">
              <FileImage className="h-4 w-4" />
              <span className="truncate max-w-[200px]">{currentFile.name}</span>
              <span>({(currentFile.size / 1024).toFixed(0)} KB)</span>
            </div>
            <button
              onClick={clearFile}
              className="p-1 hover:bg-gray-700 rounded transition-colors"
            >
              <X className="h-4 w-4 text-gray-400" />
            </button>
          </div>
          <img
            src={preview}
            alt="Architecture diagram"
            className="w-full max-h-[300px] object-contain rounded-lg"
          />
        </div>
      </div>
    );
  }

  return (
    <div
      {...getRootProps()}
      className={`
        rounded-xl border-2 border-dashed p-8 text-center cursor-pointer transition-all duration-200
        ${isDragActive
          ? 'border-green-500 bg-green-500/10'
          : 'border-gray-700 bg-gray-900/30 hover:border-gray-500 hover:bg-gray-900/50'
        }
      `}
    >
      <input {...getInputProps()} />
      <div className="flex flex-col items-center gap-3">
        <div className={`p-4 rounded-full ${isDragActive ? 'bg-green-500/20' : 'bg-gray-800'}`}>
          {isDragActive ? (
            <Image className="h-8 w-8 text-green-400" />
          ) : (
            <Upload className="h-8 w-8 text-gray-400" />
          )}
        </div>
        <div>
          <p className="text-sm font-medium text-gray-300">
            {isDragActive ? 'Drop your diagram here' : 'Drag & drop your architecture diagram'}
          </p>
          <p className="text-xs text-gray-500 mt-1">
            PNG, JPG, SVG up to 10MB
          </p>
        </div>
      </div>
    </div>
  );
}
```

## File 4: app/page.tsx

```typescript
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
    <div className="min-h-screen bg-black">
      {/* Header */}
      <header className="sticky top-0 z-50 border-b border-gray-800 bg-black/80 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-gradient-to-br from-red-500 to-green-500 rounded-lg">
              <Zap className="h-5 w-5 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white tracking-tight">ArchIntel</h1>
              <p className="text-xs text-gray-500">Architecture Intelligence Platform</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-gray-600">Powered by</span>
            <span className="text-xs font-medium text-gray-400">Gemini 2.5 Flash + 1.5 Pro</span>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Left: Upload Zone */}
          <div className="lg:col-span-1 space-y-4">
            <h2 className="text-sm font-medium text-gray-400 uppercase tracking-wider">
              Architecture Diagram
            </h2>
            <UploadZone onFileSelect={setDiagramFile} currentFile={diagramFile} />

            {diagramFile && (
              <div className="p-3 bg-gray-900/50 rounded-lg border border-gray-800">
                <p className="text-xs text-gray-500">
                  Select a tab on the right to analyze security threats, estimate costs, or start a voice conversation.
                </p>
              </div>
            )}
          </div>

          {/* Right: Analysis Tabs */}
          <div className="lg:col-span-2">
            <Tabs defaultValue="voice" className="w-full">
              <TabsList className="grid w-full grid-cols-3 bg-gray-900 border border-gray-800">
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
```

## Design Requirements
- Everything is dark mode (black background `bg-black`, gray-900 cards)
- Red accent for security/threats, green accent for cost/money
- Gradient logo icon (red to green) representing the dual nature
- Sticky header with backdrop blur
- Responsive: stacked on mobile, 1/3 + 2/3 grid on desktop
- All text in white/gray scale. No bright colors except accents
- Streaming text should use the `.streaming-cursor` class while loading
- Code blocks (Terraform) use syntax highlighting with atom-one-dark theme

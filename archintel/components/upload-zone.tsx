'use client';

import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, Image, X, FileImage } from 'lucide-react';

interface UploadZoneProps {
  onFileSelect: (file: File | null) => void;
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
    maxSize: 10 * 1024 * 1024,
  });

  const clearFile = () => {
    setPreview(null);
    onFileSelect(null);
  };

  if (preview && currentFile) {
    return (
      <div className="relative group">
        <div className="rounded-xl border border-border bg-card p-2 overflow-hidden">
          <div className="flex items-center justify-between mb-2 px-2">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <FileImage className="h-4 w-4" />
              <span className="truncate max-w-[200px]">{currentFile.name}</span>
              <span>({(currentFile.size / 1024).toFixed(0)} KB)</span>
            </div>
            <button
              onClick={clearFile}
              className="p-1 hover:bg-secondary rounded transition-colors"
            >
              <X className="h-4 w-4 text-muted-foreground" />
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
          : 'border-border bg-card/30 hover:border-muted-foreground/30 hover:bg-card/50'
        }
      `}
    >
      <input {...getInputProps()} />
      <div className="flex flex-col items-center gap-3">
        <div className={`p-4 rounded-full ${isDragActive ? 'bg-green-500/20' : 'bg-secondary'}`}>
          {isDragActive ? (
            <Image className="h-8 w-8 text-green-400" />
          ) : (
            <Upload className="h-8 w-8 text-muted-foreground" />
          )}
        </div>
        <div>
          <p className="text-sm font-medium text-foreground/80">
            {isDragActive ? 'Drop your diagram here' : 'Drag & drop your architecture diagram'}
          </p>
          <p className="text-xs text-muted-foreground mt-1">
            PNG, JPG, SVG up to 10MB
          </p>
        </div>
      </div>
    </div>
  );
}

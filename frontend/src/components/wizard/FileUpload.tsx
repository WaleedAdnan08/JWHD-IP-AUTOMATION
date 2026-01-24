import React, { useCallback, useState } from 'react';
import { Upload, FileText, AlertCircle, Loader2 } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';

interface FileUploadProps {
  onFileSelect: (file: File) => void;
  isLoading?: boolean;
  error?: string | null;
}

export const FileUpload: React.FC<FileUploadProps> = ({ 
  onFileSelect, 
  isLoading = false,
  error = null 
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      // Accept PDF or CSV files
      if (file.type === 'application/pdf' || file.type === 'text/csv' || file.name.endsWith('.csv')) {
        setSelectedFile(file);
        onFileSelect(file);
      }
    }
  }, [onFileSelect]);

  const handleFileInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setSelectedFile(file);
      onFileSelect(file);
    }
  }, [onFileSelect]);

  return (
    <div className="w-full max-w-xl mx-auto">
      <Card className={cn(
        "border-2 border-dashed transition-all duration-200",
        isDragging ? "border-primary bg-primary/5" : "border-gray-200",
        error ? "border-red-500 bg-red-50" : ""
      )}>
        <CardContent className="flex flex-col items-center justify-center p-10 space-y-4">
          <div className="relative">
            {isLoading ? (
              <div className="h-16 w-16 flex items-center justify-center rounded-full bg-primary/10 animate-pulse">
                <Loader2 className="h-8 w-8 text-primary animate-spin" />
              </div>
            ) : (
              <div className={cn(
                "h-16 w-16 flex items-center justify-center rounded-full",
                error ? "bg-red-100" : "bg-primary/10"
              )}>
                {error ? (
                  <AlertCircle className="h-8 w-8 text-red-600" />
                ) : (
                  <Upload className="h-8 w-8 text-primary" />
                )}
              </div>
            )}
          </div>

          <div className="text-center space-y-2">
            <h3 className="text-lg font-semibold">
              {isLoading ? "Processing Document..." : "Upload your Patent Cover Sheet (PDF) or Inventor List (CSV)"}
            </h3>
            <p className="text-sm text-muted-foreground max-w-xs mx-auto">
              {error || "Drag and drop your PDF or CSV here, or click to browse"}
            </p>
          </div>

          {!isLoading && (
            <div className="flex flex-col items-center gap-4 w-full">
              <input
                type="file"
                accept=".pdf,.csv"
                className="hidden"
                id="file-upload"
                onChange={handleFileInput}
                disabled={isLoading}
              />
              <label htmlFor="file-upload">
                <Button variant="outline" className="cursor-pointer" asChild>
                  <span>Select File</span>
                </Button>
              </label>

              {selectedFile && !error && (
                <div className="flex items-center gap-2 text-sm text-green-600 bg-green-50 px-3 py-1 rounded-full">
                  <FileText className="h-4 w-4" />
                  <span className="truncate max-w-[200px]">{selectedFile.name}</span>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      <div className="mt-6 text-center">
        <p className="text-xs text-muted-foreground">
          Supported Formats: PDF, CSV (Max 50MB)
        </p>
      </div>
    </div>
  );
};
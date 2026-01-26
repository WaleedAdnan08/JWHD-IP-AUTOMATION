import React, { useState } from 'react';
import { FileUpload } from './FileUpload';
import { InventorTable, Inventor } from './InventorTable';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { CheckCircle2, AlertTriangle, ArrowRight, Download, RefreshCw } from 'lucide-react';
import api from '@/lib/axios';
import { Input } from '@/components/ui/input';

type WizardStep = 'upload' | 'review' | 'success';

interface ApplicationMetadata {
  title?: string;
  application_number?: string;
  entity_status?: string;
  inventors: Inventor[];
}

export const ApplicationWizard = () => {
  const [step, setStep] = useState<WizardStep>('upload');
  const [isLoading, setIsLoading] = useState(false);
  const [processingStatus, setProcessingStatus] = useState<string>('');
  const [error, setError] = useState<string | null>(null);
  
  // Data State
  const [metadata, setMetadata] = useState<ApplicationMetadata>({ inventors: [] });
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null);

  const pollJobStatus = async (jobId: string): Promise<void> => {
    const pollInterval = 2000; // 2 seconds
    const maxAttempts = 60; // 2 minutes timeout
    
    for (let i = 0; i < maxAttempts; i++) {
      try {
        const response = await api.get(`/jobs/${jobId}`);
        const job = response.data;
        
        if (job.status === 'completed') {
          return;
        } else if (job.status === 'failed') {
          throw new Error(job.error_details || 'Processing failed');
        }
        
        setProcessingStatus(`Processing... ${job.progress_percentage}%`);
        await new Promise(resolve => setTimeout(resolve, pollInterval));
      } catch (err) {
        throw err;
      }
    }
    throw new Error('Processing timed out');
  };

  const handleFileUpload = async (file: File) => {
    setIsLoading(true);
    setError(null);
    setProcessingStatus('Uploading...');
    
    const formData = new FormData();
    formData.append('file', file);

    const isCsv = file.name.toLowerCase().endsWith('.csv') || file.type === 'text/csv';

    try {
      if (isCsv) {
        // CSV Workflow (Sync)
        const response = await api.post('/applications/parse-csv', formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
        });
        
        setMetadata({
          inventors: response.data,
          title: '',
          application_number: ''
        });
      } else {
        // PDF Workflow (Async)
        // 1. Upload
        formData.append('document_type', 'cover_sheet');
        const uploadResponse = await api.post('/documents/upload', formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
        });
        const documentId = uploadResponse.data.id || uploadResponse.data._id; // Handle both aliases just in case

        // 2. Start Parsing
        setProcessingStatus('Initiating extraction...');
        const parseResponse = await api.post(`/documents/${documentId}/parse`);
        const jobId = parseResponse.data.job_id;

        // 3. Poll for Completion
        await pollJobStatus(jobId);

        // 4. Fetch Results
        setProcessingStatus('Finalizing...');
        const docResponse = await api.get(`/documents/${documentId}`);
        if (docResponse.data.extraction_data) {
          setMetadata(docResponse.data.extraction_data);
        } else {
          throw new Error('No extraction data found in document');
        }
      }

      setStep('review');
    } catch (err: any) {
      console.error('Processing failed:', err);
      // Default error message
      let errorMessage = `Failed to process ${isCsv ? 'CSV' : 'document'}. Please try again.`;
      
      // Use detailed error from backend if available
      if (err.response?.data?.detail) {
        const detail = err.response.data.detail;
        if (typeof detail === 'string') {
          errorMessage = detail;
        } else if (Array.isArray(detail)) {
          // Handle FastAPI validation errors (array of objects)
          errorMessage = detail.map((e: any) => e.msg || JSON.stringify(e)).join(', ');
        } else if (typeof detail === 'object') {
          errorMessage = JSON.stringify(detail);
        }
      } else if (err.message) {
         // Fallback to axios error message if no response data
         errorMessage = err.message;
      }
      
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const handleGenerateADS = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await api.post('/applications/generate-ads', metadata);
      setDownloadUrl(response.data.download_url);
      setStep('success');
    } catch (err: any) {
      console.error('Generation failed:', err);
      let errorMessage = 'Failed to generate ADS. Please try again.';
      
      if (err.response?.data?.detail) {
        const detail = err.response.data.detail;
        if (typeof detail === 'string') {
          errorMessage = detail;
        } else if (Array.isArray(detail)) {
          errorMessage = detail.map((e: any) => e.msg || JSON.stringify(e)).join(', ');
        } else if (typeof detail === 'object') {
          errorMessage = JSON.stringify(detail);
        }
      }
      
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const resetWizard = () => {
    setStep('upload');
    setMetadata({ inventors: [] });
    setDownloadUrl(null);
    setError(null);
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      {/* Progress Stepper */}
      <div className="flex items-center justify-center space-x-4 mb-8">
        <div className={`flex items-center space-x-2 ${step === 'upload' ? 'text-primary font-bold' : 'text-muted-foreground'}`}>
          <div className="h-8 w-8 rounded-full border-2 flex items-center justify-center border-current">1</div>
          <span>Upload</span>
        </div>
        <div className="h-px w-16 bg-border" />
        <div className={`flex items-center space-x-2 ${step === 'review' ? 'text-primary font-bold' : 'text-muted-foreground'}`}>
          <div className="h-8 w-8 rounded-full border-2 flex items-center justify-center border-current">2</div>
          <span>Review</span>
        </div>
        <div className="h-px w-16 bg-border" />
        <div className={`flex items-center space-x-2 ${step === 'success' ? 'text-primary font-bold' : 'text-muted-foreground'}`}>
          <div className="h-8 w-8 rounded-full border-2 flex items-center justify-center border-current">3</div>
          <span>Download</span>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded relative flex items-center gap-2">
          <AlertTriangle className="h-5 w-5" />
          <span>{error}</span>
        </div>
      )}

      {step === 'upload' && (
        <div className="space-y-6">
          <div className="text-center space-y-2">
            <h1 className="text-3xl font-bold tracking-tight">New Application</h1>
            <p className="text-muted-foreground">Upload your Patent Cover Sheet (PDF) or Inventor List (CSV) to get started.</p>
          </div>
          <FileUpload onFileSelect={handleFileUpload} isLoading={isLoading} error={error} />
          {isLoading && processingStatus && (
            <div className="text-center text-sm text-muted-foreground animate-pulse">
              {processingStatus}
            </div>
          )}
        </div>
      )}

      {step === 'review' && (
        <Card>
          <CardHeader>
            <CardTitle>Review Extracted Data</CardTitle>
            <CardDescription>
              Please verify the information below before generating the ADS.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <label className="text-sm font-medium">Application Title</label>
                <Input 
                  value={metadata.title || ''} 
                  onChange={(e) => setMetadata({...metadata, title: e.target.value})}
                  placeholder="Enter Title"
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Application Number</label>
                <Input 
                  value={metadata.application_number || ''} 
                  onChange={(e) => setMetadata({...metadata, application_number: e.target.value})}
                  placeholder="e.g. 17/123,456"
                />
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Inventors ({metadata.inventors.length})</label>
              <InventorTable 
                inventors={metadata.inventors} 
                setInventors={(invs) => setMetadata({...metadata, inventors: invs})} 
              />
            </div>

            <div className="flex justify-end gap-4 pt-4">
              <Button variant="outline" onClick={() => setStep('upload')}>Back</Button>
              <Button onClick={handleGenerateADS} disabled={isLoading}>
                {isLoading ? (
                  <>
                    <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                    {processingStatus || 'Processing...'}
                  </>
                ) : (
                  <>
                    Generate ADS <ArrowRight className="ml-2 h-4 w-4" />
                  </>
                )}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {step === 'success' && (
        <Card className="text-center py-10">
          <CardContent className="space-y-6 flex flex-col items-center">
            <div className="h-20 w-20 bg-green-100 text-green-600 rounded-full flex items-center justify-center">
              <CheckCircle2 className="h-10 w-10" />
            </div>
            
            <div className="space-y-2">
              <h2 className="text-2xl font-bold">ADS Generated Successfully!</h2>
              <p className="text-muted-foreground">Your Application Data Sheet is ready for download.</p>
            </div>

            <div className="flex gap-4">
              <Button variant="outline" onClick={resetWizard}>Start Over</Button>
              {downloadUrl && (
                <Button asChild className="bg-green-600 hover:bg-green-700">
                  <a href={downloadUrl} target="_blank" rel="noopener noreferrer">
                    <Download className="mr-2 h-4 w-4" />
                    Download PDF
                  </a>
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};
import React, { useState } from 'react';
import { FileUpload } from './FileUpload';
import { InventorTable, Inventor } from './InventorTable';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { CheckCircle2, AlertTriangle, ArrowRight, Download, RefreshCw } from 'lucide-react';
import api from '@/lib/axios';
import { Input } from '@/components/ui/input';

type WizardStep = 'upload' | 'review' | 'success';

interface Applicant {
    name?: string;
    street_address?: string;
    city?: string;
    state?: string;
    country?: string;
    zip_code?: string;
}

interface ApplicationMetadata {
  title?: string;
  application_number?: string;
  entity_status?: string;
  inventors: Inventor[];
  applicant?: Applicant;
  total_drawing_sheets?: number;
}

export const ApplicationWizard = () => {
  const [step, setStep] = useState<WizardStep>('upload');
  const [isLoading, setIsLoading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<number>(0);
  const [processingStatus, setProcessingStatus] = useState<string>('');
  const [error, setError] = useState<string | null>(null);
  
  const handleFileUploadError = (errorMessage: string) => {
    setError(errorMessage);
  };
  
  // Data State
  const [metadata, setMetadata] = useState<ApplicationMetadata>({ inventors: [], applicant: {} });
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null);

  const pollJobStatus = async (jobId: string): Promise<void> => {
    const pollInterval = 2000; // 2 seconds
    const maxAttempts = 60; // 2 minutes timeout
    
    for (let i = 0; i < maxAttempts; i++) {
      try {
        const response = await api.get(`/jobs/${jobId}`);
        const job = response.data;
        
        if (job.status === 'completed') {
          setUploadProgress(100);
          return;
        } else if (job.status === 'failed') {
          throw new Error(job.error_details || 'Processing failed');
        }
        
        // Map job progress (0-100) to UI progress
        // We already hit 100% on upload, so let's keep it there or restart
        // Better UX: Show "Processing... X%" in the status text,
        // but maybe keep the bar full or pulsating.
        // Or re-purpose the bar:
        // If we want the bar to reflect server processing, we can set it here.
        // Only update progress if it's meaningful (avoid jumping back to 0 if we were at 100)
        // Or, if we want to show server processing as a new phase, we could.
        // But for continuity, let's keep it at 100 or animate a "processing" state.
        // However, if the user sees "stuck at 30%", forcing 100% after upload (above) fixes the main issue.
        // Let's just allow server updates if they exist, but maybe keep it high.
        if (job.progress_percentage) {
             setUploadProgress(prev => Math.max(prev, job.progress_percentage || 0));
        }

        setProcessingStatus(`Processing... ${job.progress_percentage}%`);
        await new Promise(resolve => setTimeout(resolve, pollInterval));
      } catch (err) {
        throw err;
      }
    }
    throw new Error('Processing timed out');
  };

  const handleFilesUpload = async (files: File[]) => {
    setIsLoading(true);
    setUploadProgress(0);
    setError(null);
    setProcessingStatus('Processing files...');
    
    const allResults: ApplicationMetadata[] = [];
    
    try {
      // Process each file sequentially
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        const fileProgress = ((i / files.length) * 100);
        setUploadProgress(fileProgress);
        setProcessingStatus(`Processing file ${i + 1} of ${files.length}: ${file.name}`);
        
        const formData = new FormData();
        formData.append('file', file);
        const isCsv = file.name.toLowerCase().endsWith('.csv') || file.type === 'text/csv';

        const config = {
          headers: { 'Content-Type': 'multipart/form-data' },
          onUploadProgress: (progressEvent: any) => {
            const filePercent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
            const totalProgress = fileProgress + (filePercent / files.length);
            setUploadProgress(totalProgress);
          },
        };

        let fileResult: ApplicationMetadata;

        if (isCsv) {
          // CSV Workflow (Sync)
          const response = await api.post('/applications/parse-csv', formData, config);
          fileResult = {
            inventors: response.data,
            title: '',
            application_number: '',
            applicant: {}
          };
        } else {
          // PDF Workflow (Async)
          formData.append('document_type', 'cover_sheet');
          const uploadResponse = await api.post('/documents/upload', formData, config);
          const documentId = uploadResponse.data.id || uploadResponse.data._id;

          setProcessingStatus(`Extracting data from ${file.name}...`);
          const parseResponse = await api.post(`/documents/${documentId}/parse`);
          const jobId = parseResponse.data.job_id;

          await pollJobStatus(jobId);

          const docResponse = await api.get(`/documents/${documentId}`);
          if (docResponse.data.extraction_data) {
            fileResult = docResponse.data.extraction_data;
          } else {
            throw new Error(`No extraction data found in ${file.name}`);
          }
        }

        allResults.push(fileResult);
      }

      // Merge all results
      const mergedMetadata = mergeFileResults(allResults);
      setMetadata(mergedMetadata);
      setUploadProgress(100);
      setStep('review');

    } catch (err: any) {
      console.error('Processing failed:', err);
      let errorMessage = 'Failed to process files. Please try again.';
      
      if (err.response?.data?.detail) {
        const detail = err.response.data.detail;
        if (typeof detail === 'string') {
          errorMessage = detail;
        } else if (Array.isArray(detail)) {
          errorMessage = detail.map((e: any) => e.msg || JSON.stringify(e)).join(', ');
        } else if (typeof detail === 'object') {
          errorMessage = JSON.stringify(detail);
        }
      } else if (err.message) {
         errorMessage = err.message;
      }
      
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const mergeFileResults = (results: ApplicationMetadata[]): ApplicationMetadata => {
    const merged: ApplicationMetadata = {
      inventors: [],
      applicant: {},
      total_drawing_sheets: 0
    };

    for (const result of results) {
      // Use first non-empty title
      if (!merged.title && result.title) {
        merged.title = result.title;
      }

      // Use first non-empty application number
      if (!merged.application_number && result.application_number) {
        merged.application_number = result.application_number;
      }

      // Use first non-empty entity status
      if (!merged.entity_status && result.entity_status) {
        merged.entity_status = result.entity_status;
      }

      // Use first non-empty applicant
      if (!merged.applicant?.name && result.applicant?.name) {
        merged.applicant = result.applicant;
      }

      // Sum drawing sheets
      if (result.total_drawing_sheets) {
        merged.total_drawing_sheets = (merged.total_drawing_sheets || 0) + result.total_drawing_sheets;
      }

      // Merge inventors (deduplicate by full name)
      if (result.inventors) {
        for (const inventor of result.inventors) {
          const fullName = `${inventor.first_name || ''} ${inventor.middle_name || ''} ${inventor.last_name || ''}`.trim();
          const exists = merged.inventors.some(existing => {
            const existingFullName = `${existing.first_name || ''} ${existing.middle_name || ''} ${existing.last_name || ''}`.trim();
            return existingFullName === fullName;
          });
          
          if (!exists) {
            merged.inventors.push(inventor);
          }
        }
      }
    }

    return merged;
  };

  const handleGenerateADS = async () => {
    setIsLoading(true);
    setError(null);
    setProcessingStatus('Generating PDF...');

    try {
      const response = await api.post('/applications/generate-ads', metadata, {
        responseType: 'blob', // Critical for binary files
      });
      
      // Create blob link to download
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      
      // Extract filename from header if possible, else default
      // 1. Generate Unique Filename to prevent conflicts
      // This solves the "file already open in Acrobat" issue by ensuring every download has a unique path
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
      const appNum = metadata.application_number?.replace(/[\/\\]/g, '-') || 'Draft';
      const filename = `ADS_${appNum}_${timestamp}.pdf`;
      
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      
      // 2. Update status to inform user
      setProcessingStatus('Download starting...');

      // 3. Trigger download with slight delay to ensure DOM is ready
      setTimeout(() => {
        link.click();
        
        // 4. Extended cleanup delay (increased from 1s to 10s)
        // This gives Adobe Acrobat/Browser time to fully acquire the file handle
        // before we revoke the blob URL, preventing "file not found" or "zombie resource" errors.
        setTimeout(() => {
            if (link.parentNode) {
                link.parentNode.removeChild(link);
            }
            window.URL.revokeObjectURL(url);
        }, 10000);

        // Update UI state
        setDownloadUrl(null); // URL is revoked, so we can't reuse it.
        setStep('success');
      }, 500);

    } catch (err: any) {
      console.error('Generation failed:', err);
      let errorMessage = 'Failed to generate ADS. Please try again.';
      
      // Handle Blob Error Response
      if (err.response && err.response.data instanceof Blob) {
         try {
             const text = await err.response.data.text();
             const errorJson = JSON.parse(text);
             if (errorJson.detail) {
                 const detail = errorJson.detail;
                 if (typeof detail === 'string') {
                    errorMessage = detail;
                 } else if (Array.isArray(detail)) {
                    errorMessage = detail.map((e: any) => e.msg || JSON.stringify(e)).join(', ');
                 } else {
                     errorMessage = JSON.stringify(detail);
                 }
             }
         } catch (e) {
             // Failed to parse blob as JSON, stick to default
         }
      } else if (err.response?.data?.detail) {
        // Standard JSON Error handling (if responseType wasn't blob or axios handled it)
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
    setMetadata({ inventors: [], applicant: {} });
    setDownloadUrl(null);
    setError(null);
  };

  const loadMockData = () => {
    setMetadata({
        title: "System and Method for Automated Patent Processing",
        application_number: "18/123,456",
        entity_status: "Small Entity",
        total_drawing_sheets: 12,
        applicant: {
            name: "SnapDev Innovations LLC",
            street_address: "123 Tech Valley Dr, Suite 400",
            city: "San Francisco",
            state: "CA",
            zip_code: "94105",
            country: "US"
        },
        inventors: [
            {
                first_name: "Jane",
                middle_name: "Marie",
                last_name: "Doe",
                suffix: "Ph.D.",
                street_address: "456 Research Way",
                city: "Palo Alto",
                state: "CA",
                zip_code: "94301",
                country: "US",
                citizenship: "US"
            },
            {
                first_name: "John",
                middle_name: "A.",
                last_name: "Smith",
                suffix: "Jr.",
                street_address: "789 Coding Lane",
                city: "Austin",
                state: "TX",
                zip_code: "78701",
                country: "US",
                citizenship: "US"
            }
        ]
    });
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
          <FileUpload
            onFilesReady={handleFilesUpload}
            isLoading={isLoading}
            uploadProgress={uploadProgress}
            error={error}
            isProcessing={isLoading}
            onError={handleFileUploadError}
          />
          {isLoading && (
            <div className="w-full max-w-xl mx-auto space-y-2">
               {uploadProgress > 0 && (
                 <div className="h-2 w-full bg-secondary rounded-full overflow-hidden">
                    <div
                      className="h-full bg-primary transition-all duration-300 ease-out"
                      style={{ width: `${uploadProgress}%` }}
                    />
                 </div>
               )}
               <div className="text-center text-sm text-muted-foreground animate-pulse">
                  {processingStatus}
               </div>
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
               <div className="space-y-2">
                <label className="text-sm font-medium">Total Drawing Sheets</label>
                <Input
                  type="number"
                  value={metadata.total_drawing_sheets || ''}
                  onChange={(e) => setMetadata({...metadata, total_drawing_sheets: parseInt(e.target.value) || 0})}
                  placeholder="Number of sheets"
                />
              </div>
            </div>

            {/* Applicant Information Section */}
            <div className="space-y-4 border rounded-md p-4 bg-muted/20">
                <h3 className="font-medium text-base">Applicant / Company Information</h3>
                <div className="grid gap-4 md:grid-cols-2">
                    <div className="space-y-2 md:col-span-2">
                        <label className="text-sm font-medium">Name / Company</label>
                        <Input
                        value={metadata.applicant?.name || ''}
                        onChange={(e) => setMetadata({...metadata, applicant: {...metadata.applicant, name: e.target.value}})}
                        placeholder="Applicant Name or Company"
                        />
                    </div>
                     <div className="space-y-2 md:col-span-2">
                        <label className="text-sm font-medium">Street Address</label>
                        <Input
                        value={metadata.applicant?.street_address || ''}
                        onChange={(e) => setMetadata({...metadata, applicant: {...metadata.applicant, street_address: e.target.value}})}
                        placeholder="123 Business Rd"
                        />
                    </div>
                    <div className="space-y-2">
                        <label className="text-sm font-medium">City</label>
                        <Input
                        value={metadata.applicant?.city || ''}
                        onChange={(e) => setMetadata({...metadata, applicant: {...metadata.applicant, city: e.target.value}})}
                        placeholder="City"
                        />
                    </div>
                    <div className="space-y-2">
                        <label className="text-sm font-medium">State / Province</label>
                        <Input
                        value={metadata.applicant?.state || ''}
                        onChange={(e) => setMetadata({...metadata, applicant: {...metadata.applicant, state: e.target.value}})}
                        placeholder="State"
                        />
                    </div>
                     <div className="space-y-2">
                        <label className="text-sm font-medium">Postal Code</label>
                        <Input
                        value={metadata.applicant?.zip_code || ''}
                        onChange={(e) => setMetadata({...metadata, applicant: {...metadata.applicant, zip_code: e.target.value}})}
                        placeholder="Zip / Postal Code"
                        />
                    </div>
                     <div className="space-y-2">
                        <label className="text-sm font-medium">Country</label>
                        <Input
                        value={metadata.applicant?.country || ''}
                        onChange={(e) => setMetadata({...metadata, applicant: {...metadata.applicant, country: e.target.value}})}
                        placeholder="Country Code (e.g. US)"
                        />
                    </div>
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
              <Button variant="ghost" onClick={loadMockData} className="mr-auto text-muted-foreground">Load Mock Data</Button>
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
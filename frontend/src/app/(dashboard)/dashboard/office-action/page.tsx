'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import axios from '@/lib/axios';

export default function OfficeActionPage() {
    const router = useRouter();
    const [file, setFile] = useState<File | null>(null);
    const [uploading, setUploading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files.length > 0) {
            setFile(e.target.files[0]);
        }
    };

    const handleUpload = async () => {
        if (!file) {
            setError('Please select a PDF file.');
            return;
        }

        setUploading(true);
        setError(null);

        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await axios.post('/office-actions/upload', formData, {
                headers: {
                    'Content-Type': 'multipart/form-data',
                },
            });

            const { document_id, job_id } = response.data;
            // Navigate to the analysis status/dashboard page
            router.push(`/dashboard/office-action/${document_id}/analysis?jobId=${job_id}`);
        } catch (err: any) {
            console.error('Upload failed:', err);
            setError(err.response?.data?.detail || 'Upload failed. Please try again.');
        } finally {
            setUploading(false);
        }
    };

    return (
        <div className="container mx-auto p-8 max-w-2xl">
            <h1 className="text-3xl font-bold mb-8">Office Action Analyzer</h1>
            
            <Card>
                <CardHeader>
                    <CardTitle>Upload Office Action</CardTitle>
                    <CardDescription>
                        Upload a PDF of a USPTO Office Action to extract and analyze its contents.
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                    <div className="grid w-full items-center gap-1.5">
                        <Input 
                            type="file" 
                            accept=".pdf" 
                            onChange={handleFileChange}
                            disabled={uploading}
                        />
                    </div>
                    
                    {error && (
                        <div className="text-red-500 text-sm p-2 bg-red-50 rounded">
                            {error}
                        </div>
                    )}

                    <Button 
                        className="w-full" 
                        onClick={handleUpload} 
                        disabled={!file || uploading}
                    >
                        {uploading ? 'Uploading & Analyzing...' : 'Analyze Document'}
                    </Button>
                </CardContent>
            </Card>
        </div>
    );
}
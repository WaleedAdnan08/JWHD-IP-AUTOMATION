'use client';

import React, { useEffect, useState } from 'react';
import { useParams, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import axios from '@/lib/axios';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';

interface JobStatus {
    status: string;
    progress_percentage: number;
    error_details?: string;
}

interface OfficeActionData {
    header: any;
    claims_status: any[];
    rejections: any[];
    objections: any[];
    other_statements: any[];
}

export default function AnalysisPage() {
    const params = useParams();
    const searchParams = useSearchParams();
    const documentId = params.id as string;
    const jobId = searchParams.get('jobId');

    const [jobStatus, setJobStatus] = useState<JobStatus | null>(null);
    const [data, setData] = useState<OfficeActionData | null>(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);

    // Poll for job status
    useEffect(() => {
        if (!jobId || data) return;

        const interval = setInterval(async () => {
            try {
                const res = await axios.get(`/jobs/${jobId}`);
                setJobStatus(res.data);

                if (res.data.status === 'completed') {
                    clearInterval(interval);
                    fetchData();
                } else if (res.data.status === 'failed') {
                    clearInterval(interval);
                    setLoading(false);
                }
            } catch (err) {
                console.error("Error polling job:", err);
            }
        }, 2000);

        return () => clearInterval(interval);
    }, [jobId, data]);

    const fetchData = async () => {
        try {
            const res = await axios.get(`/office-actions/${documentId}`);
            setData(res.data);
        } catch (err) {
            console.error("Error fetching data:", err);
        } finally {
            setLoading(false);
        }
    };

    const handleSave = async () => {
        if (!data) return;
        setSaving(true);
        try {
            await axios.put(`/office-actions/${documentId}`, data);
            alert("Saved successfully!");
        } catch (err) {
            console.error("Save failed:", err);
            alert("Failed to save changes.");
        } finally {
            setSaving(false);
        }
    };
    
    const handleDownloadReport = async () => {
        try {
            const response = await axios.get(`/office-actions/${documentId}/report`, {
                responseType: 'blob',
            });
            const url = window.URL.createObjectURL(new Blob([response.data]));
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', `Office_Action_Report_${documentId}.docx`);
            document.body.appendChild(link);
            link.click();
            link.remove();
        } catch (err) {
            console.error("Download failed:", err);
            alert("Failed to download report.");
        }
    };

    if (loading || (jobStatus && jobStatus.status !== 'completed' && jobStatus.status !== 'failed')) {
        return (
            <div className="container mx-auto p-8 text-center">
                <h2 className="text-2xl font-bold mb-4">Analyzing Document...</h2>
                <div className="w-full bg-gray-200 rounded-full h-4 mb-4">
                    <div 
                        className="bg-blue-600 h-4 rounded-full transition-all duration-500" 
                        style={{ width: `${jobStatus?.progress_percentage || 0}%` }}
                    ></div>
                </div>
                <p className="text-muted-foreground">Status: {jobStatus?.status || 'Initializing'} ({jobStatus?.progress_percentage || 0}%)</p>
            </div>
        );
    }

    if (jobStatus?.status === 'failed') {
        return (
            <div className="container mx-auto p-8 text-center">
                <h2 className="text-2xl font-bold text-red-600 mb-4">Analysis Failed</h2>
                <p className="mb-4">{jobStatus.error_details}</p>
                <Button asChild>
                    <Link href="/dashboard/office-action">Try Again</Link>
                </Button>
            </div>
        );
    }

    if (!data) return <div>No data loaded.</div>;

    return (
        <div className="container mx-auto p-8">
            <div className="flex justify-between items-center mb-8">
                <h1 className="text-3xl font-bold">Analysis Results</h1>
                <div className="space-x-4">
                    <Button variant="outline" onClick={handleSave} disabled={saving}>
                        {saving ? 'Saving...' : 'Save Changes'}
                    </Button>
                    <Button onClick={handleDownloadReport}>Download Word Report</Button>
                </div>
            </div>

            <div className="grid gap-6">
                {/* Header Info */}
                <Card>
                    <CardHeader><CardTitle>Application Details</CardTitle></CardHeader>
                    <CardContent className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="text-sm font-medium">Application Number</label>
                            <Input 
                                value={data.header.application_number} 
                                onChange={(e) => setData({...data, header: {...data.header, application_number: e.target.value}})}
                            />
                        </div>
                        <div>
                            <label className="text-sm font-medium">Mailing Date</label>
                            <Input 
                                value={data.header.office_action_date} 
                                onChange={(e) => setData({...data, header: {...data.header, office_action_date: e.target.value}})}
                            />
                        </div>
                         <div>
                            <label className="text-sm font-medium">Response Deadline</label>
                            <Input 
                                value={data.header.response_deadline} 
                                onChange={(e) => setData({...data, header: {...data.header, response_deadline: e.target.value}})}
                            />
                        </div>
                    </CardContent>
                </Card>

                {/* Rejections */}
                <Card>
                    <CardHeader><CardTitle>Rejections</CardTitle></CardHeader>
                    <CardContent className="space-y-6">
                        {data.rejections.map((rej, idx) => (
                            <div key={idx} className="border p-4 rounded-lg">
                                <div className="flex justify-between mb-2">
                                    <h3 className="font-bold">Rejection #{idx + 1} ({rej.rejection_type})</h3>
                                    <Button variant="ghost" size="sm" className="text-red-500">Remove</Button>
                                </div>
                                <div className="space-y-2">
                                    <div>
                                        <label className="text-sm font-medium">Examiner Reasoning</label>
                                        <Textarea 
                                            value={rej.examiner_reasoning} 
                                            onChange={(e) => {
                                                const newRejections = [...data.rejections];
                                                newRejections[idx].examiner_reasoning = e.target.value;
                                                setData({...data, rejections: newRejections});
                                            }}
                                            rows={4}
                                        />
                                    </div>
                                    {/* Add more fields as needed */}
                                </div>
                            </div>
                        ))}
                        {data.rejections.length === 0 && <p className="text-muted-foreground">No rejections detected.</p>}
                    </CardContent>
                </Card>

                 {/* Claims Status */}
                <Card>
                    <CardHeader><CardTitle>Claims Status</CardTitle></CardHeader>
                    <CardContent>
                         <div className="grid grid-cols-3 gap-2 font-bold mb-2">
                            <div>Claim No.</div>
                            <div>Status</div>
                            <div>Type</div>
                        </div>
                        {data.claims_status.map((claim, idx) => (
                            <div key={idx} className="grid grid-cols-3 gap-2 mb-2 items-center">
                                <Input 
                                    value={claim.claim_number}
                                    onChange={(e) => {
                                         const newClaims = [...data.claims_status];
                                         newClaims[idx].claim_number = e.target.value;
                                         setData({...data, claims_status: newClaims});
                                    }}
                                />
                                <Input 
                                    value={claim.status}
                                    onChange={(e) => {
                                         const newClaims = [...data.claims_status];
                                         newClaims[idx].status = e.target.value;
                                         setData({...data, claims_status: newClaims});
                                    }}
                                />
                                <Input 
                                    value={claim.dependency_type}
                                    onChange={(e) => {
                                         const newClaims = [...data.claims_status];
                                         newClaims[idx].dependency_type = e.target.value;
                                         setData({...data, claims_status: newClaims});
                                    }}
                                />
                            </div>
                        ))}
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
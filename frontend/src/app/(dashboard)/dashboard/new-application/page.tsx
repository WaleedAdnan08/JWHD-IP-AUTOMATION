'use client';

import React from 'react';
import { ApplicationWizard } from '@/components/wizard/ApplicationWizard';

export default function NewApplicationPage() {
  return (
    <div className="container mx-auto py-8">
      <ApplicationWizard />
    </div>
  );
}
# Debug: Start Extraction Button Not Appearing

## Issue Summary
The "Start Extraction" button in the FileUpload component is not visible when files are selected.

## Root Causes Identified & Fixed

### 1. React State Dependencies Issue ✅ FIXED
**Problem:** The `addFiles` callback depended on `selectedFiles` state, causing stale closures.
**Solution:** Changed to functional state updates using `setSelectedFiles(currentFiles => ...)`.

### 2. Prop Logic Confusion ✅ FIXED  
**Problem:** `isLoading` was used for both upload progress AND button visibility.
**Solution:** Added separate `isProcessing` prop for button visibility control.

## Changes Made

### FileUpload.tsx
1. Added `isProcessing?: boolean` to props interface
2. Changed `addFiles` to use functional state updates (no dependency on `selectedFiles`)
3. Changed `removeFile` to use functional state updates
4. Updated button visibility condition from `!isLoading` to `!isProcessing`
5. Removed debugging console.logs that could interfere with rendering

### ApplicationWizard.tsx
1. Added `isProcessing={isLoading}` prop to FileUpload component

## Button Visibility Logic
```javascript
// Button appears when:
selectedFiles.length > 0 && !isProcessing

// Test cases verified:
✅ No files selected → Button hidden
✅ Files selected, not processing → Button visible  
✅ Files selected, processing → Button hidden
✅ Multiple files selected, not processing → Button visible
```

## Testing Instructions
1. Navigate to `/dashboard/new-application`
2. Select one or more files (PDF, CSV, or DOCX)
3. Verify "Start Extraction" button appears below the file list
4. Click button to verify it triggers processing
5. Verify button disappears during processing

## Expected Behavior
- Button should appear immediately after selecting files
- Button text should show file count: "Start Extraction (2 files)"
- Button should be full-width and blue
- Button should disappear when processing starts
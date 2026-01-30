# n8n Workflow Improvements - Complete Summary

## ✅ All Improvements Completed

### 1. ✅ File Upload Functionality Added

The workflow now properly handles file uploads to VirusTotal:

**New Flow:**
1. **Download File** - Downloads the file from Django server using `file_url`
2. **Upload to VirusTotal** - Uploads the file to VirusTotal for scanning
3. **Wait for Scan** - Waits 5 seconds for VirusTotal to process the file
4. **Query VirusTotal** - Queries VirusTotal for scan results using the file hash

**Previous Flow (Broken):**
- Only queried VirusTotal by hash (would fail if file wasn't already in database)

**New Nodes Added:**
- `Download File` - HTTP Request node to download file from `file_url`
- `Upload to VirusTotal` - HTTP Request node to POST file to VirusTotal API
- `Wait for Scan` - Wait node (5 seconds) for VirusTotal processing
- `Query VirusTotal` - Renamed from "HTTP Request" for clarity

### 2. ✅ Test Script Created

Created `test_workflow_data.py` to verify workflow receives correct data:

**Usage:**
```bash
python test_workflow_data.py [base_url] [n8n_webhook_url]
```

**What it does:**
- Shows the expected payload structure Django sends to n8n
- Displays n8n expression examples for accessing data
- Tests webhook connectivity (if n8n is configured)
- Provides verification checklist
- Lists common issues and solutions

**Example:**
```bash
python test_workflow_data.py http://localhost:8000
```

### 3. ✅ Better Error Handling & Logging

**Error Handling Improvements:**
- All HTTP Request nodes have `onError: continueRegularOutput` to prevent workflow crashes
- Added descriptive error notes to each node explaining what errors to expect
- Added null coalescing operator (`??`) to If1 condition to handle missing data gracefully

**Node Notes Added:**
- **Download File**: "⚠️ Error: File download failed - check file_url is accessible"
- **Upload to VirusTotal**: "⚠️ Error: Upload failed - check API key and file size limits"
- **Query VirusTotal**: "⚠️ Error: Query failed - file may not be in database yet"
- **Quarantine User Auto**: "⚠️ Error: Quarantine failed - check API endpoint and user_id"

**Improved Condition:**
- Changed `{{ $json.data.attributes.last_analysis_stats.malicious }}` 
- To: `{{ $json.data?.attributes?.last_analysis_stats?.malicious ?? 0 }}`
- This prevents errors if VirusTotal response structure is different

## Workflow Flow Diagram

```
Webhook (receives incident data)
    ↓
Send Telegram Alert
    ↓
If (file_hash exists?)
    ├─ YES → Download File
    │          ↓
    │       Upload to VirusTotal
    │          ↓
    │       Wait for Scan (5s)
    │          ↓
    │       Query VirusTotal
    │          ↓
    │       If1 (malicious > 0?)
    │          ├─ YES → Quarantine User Auto
    │          │          ↓
    │          │       Send Security Alert (Telegram)
    │          │
    │          └─ NO → Send Clean Message (Telegram)
    │
    └─ NO → Send "No attachment" message
```

## Key Fixes Applied

### Fix 1: Dynamic VirusTotal URL
- **Before**: Hardcoded hash `275a021bbfb6489e54d471899f7db9d1663fc695ec2fe2a2c4538aabf651fd0f`
- **After**: `{{ $node["Webhook"].json.body.file_hash }}`

### Fix 2: User ID in Quarantine
- **Before**: Using `reported_by_id` (could be undefined)
- **After**: Using `user_id` (guaranteed to exist)

### Fix 3: File Upload Process
- **Before**: Only queried by hash (fails if file not in database)
- **After**: Downloads → Uploads → Waits → Queries (works for new files)

## Testing Checklist

### 1. Test Workflow Data Script
```bash
cd C:\Users\zhiwei.cheong\SIRTS_Project
python test_workflow_data.py
```

### 2. Test Quarantine API
```bash
python test_quarantine_api.py 3
```

### 3. Test Complete Flow
1. Log in as user 3
2. Report an incident with a file attachment
3. Check n8n execution logs:
   - [ ] Webhook received data
   - [ ] File downloaded successfully
   - [ ] File uploaded to VirusTotal
   - [ ] VirusTotal query returned results
   - [ ] If malicious > 0, quarantine executed
   - [ ] Telegram notifications sent

## Importing Updated Workflow

1. Open n8n
2. Go to your workflow
3. Click "Import from File" or "Replace Workflow"
4. Upload: `c:\Users\zhiwei.cheong\Downloads\My workflow (5).json`
5. Verify all nodes are connected correctly
6. Test with a sample incident

## Important Notes

### VirusTotal API Requirements
- **API Key**: Must be configured in n8n credentials (Header Auth)
- **Rate Limits**: VirusTotal has rate limits (4 requests/minute for free tier)
- **File Size**: Max 650MB
- **Scan Time**: Can take 10-60 seconds (5 second wait may need adjustment)

### File URL Accessibility
- Django must have `EXTERNAL_BASE_URL` configured in settings
- File must be accessible from n8n's network location
- If n8n is in Docker, use `host.docker.internal` for localhost

### Error Recovery
- If file upload fails, the workflow will still try to query by hash
- If query fails, the workflow continues (won't crash)
- Check n8n execution logs for detailed error messages

## Troubleshooting

### Issue: File download fails
**Solution**: Check `file_url` in webhook payload, verify file is accessible

### Issue: VirusTotal upload fails
**Solution**: Check API key, verify file size < 650MB, check rate limits

### Issue: Quarantine not executing
**Solution**: 
1. Check If1 condition - verify `malicious` count > 0
2. Check Quarantine node - verify `user_id` is numeric
3. Check n8n execution logs for errors

### Issue: User not frozen
**Solution**: 
1. Test quarantine API directly: `python test_quarantine_api.py 3`
2. Check Django logs for API errors
3. Verify user exists and is active

## Next Steps

1. ✅ Import updated workflow to n8n
2. ✅ Test with user 3 and a malicious file
3. ✅ Monitor n8n execution logs
4. ✅ Verify user 3 is quarantined after malicious file detection

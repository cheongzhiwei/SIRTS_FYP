# EICAR Auto-Quarantine Fix Summary

## Issue Found
The "Wait for Scan" node in your workflow had **empty parameters**, which means it wasn't actually waiting for VirusTotal to process the file before querying. This could cause the query to happen before the scan is complete.

## Fixes Applied

### Fix 1: Wait for Scan Node
**Before**: 
```json
"parameters": {}
```

**After**:
```json
"parameters": {
  "amount": 5,
  "unit": "seconds"
}
```

This ensures the workflow waits 5 seconds after uploading before querying VirusTotal.

### Fix 2: Query VirusTotal Uses Dynamic Hash
✅ Already fixed - uses `{{ $node["Webhook"].json.body.file_hash }}`

### Fix 3: Upload to VirusTotal Has File Parameter
✅ Already fixed - includes `bodyParameters` with file data

## Testing Steps

1. **Import the Fixed Workflow**:
   - Go to n8n
   - Import: `c:\Users\zhiwei.cheong\Downloads\My workflow (6).json`
   - Make sure workflow is **Active**

2. **Test with EICAR.txt**:
   - Log in as a test user (e.g., user 3)
   - Report an incident with EICAR.txt file
   - The workflow should:
     - Download the file
     - Upload to VirusTotal
     - **Wait 5 seconds** (now fixed!)
     - Query by hash
     - Detect EICAR as malicious (50+ detections)
     - Call quarantine API
     - Deactivate user automatically

3. **Verify in n8n**:
   - Go to n8n → Executions
   - Find the execution
   - Check each node:
     - **Wait for Scan**: Should show it waited 5 seconds
     - **Query VirusTotal**: Should return scan results with `malicious > 0`
     - **If1**: Should evaluate to `true`
     - **Quarantine User Auto**: Should show success response

4. **Verify in Django Admin**:
   - Go to Django Admin → Users
   - Find the user who uploaded EICAR
   - **"Active" checkbox should be UNCHECKED**

## Debugging Checklist

If it still doesn't work, check:

- [ ] Workflow is **Active** in n8n
- [ ] "Wait for Scan" has `amount: 5, unit: seconds`
- [ ] "Query VirusTotal" uses dynamic hash
- [ ] "Quarantine User Auto" uses `user_id` from webhook
- [ ] Django server is running
- [ ] n8n can reach Django at `http://host.docker.internal:8000`

## Expected Workflow Flow

```
Webhook (receives incident with EICAR.txt)
  ↓
Send Telegram Alert
  ↓
If (file_hash exists?) → YES
  ↓
Download File (EICAR.txt)
  ↓
Upload to VirusTotal
  ↓
Wait for Scan (5 seconds) ← FIXED: Now actually waits!
  ↓
Query VirusTotal (by file_hash)
  ↓
If1 (malicious > 0?) → YES (EICAR has 50+ detections)
  ↓
Quarantine User Auto
  POST http://host.docker.internal:8000/api/quarantine-user/
  Body: {"user_id": 3}
  ↓
Send Security Alert (Telegram)
```

## EICAR File Info

- **SHA256**: `131f95c51cc819465fa1797f6ccacf9d494daff26151609079e4e6d8c6c0d0b0`
- **Expected Detections**: 50+ antivirus engines
- **Purpose**: Standard test file for antivirus software

## Still Not Working?

1. Check n8n execution logs - look for errors in each node
2. Verify the "Wait for Scan" node actually waited (check execution time)
3. Check if "Query VirusTotal" returned results with `malicious > 0`
4. Verify "Quarantine User Auto" was called and returned success
5. Test quarantine API directly:
   ```bash
   python -c "import requests; import json; response = requests.post('http://localhost:8000/api/quarantine-user/', json={'user_id': 3}, headers={'Content-Type': 'application/json'}); print(json.dumps(response.json(), indent=2))"
   ```

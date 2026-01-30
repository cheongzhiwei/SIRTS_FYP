# EICAR Test File - Auto-Quarantine Debugging Guide

## Issue: EICAR.txt Not Triggering Auto-Quarantine

If EICAR.txt is uploaded but the user is not automatically quarantined, follow these debugging steps:

## Step 1: Verify EICAR is Detected by VirusTotal

EICAR is a standard test file that should be detected by VirusTotal. The EICAR file hash is:
- **SHA256**: `131f95c51cc819465fa1797f6ccacf9d494daff26151609079e4e6d8c6c0d0b0`
- **Content**: `X5O!P%@AP[4\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*`

### Check in n8n:
1. Go to n8n → Executions
2. Find the execution where EICAR was uploaded
3. Click on **"Query VirusTotal"** node
4. Check the output - it should show:
   ```json
   {
     "data": {
       "attributes": {
         "last_analysis_stats": {
           "malicious": 50+  // Should be > 0
         }
       }
     }
   }
   ```

## Step 2: Verify the "If1" Condition

The workflow should check if `malicious > 0`. Check the condition:

1. In n8n, click on **"If1"** node
2. Verify the condition is:
   ```
   {{ $json.data?.attributes?.last_analysis_stats?.malicious ?? 0 }} > 0
   ```
3. Check if the condition evaluated to `true` or `false`

## Step 3: Verify Quarantine API is Called

1. In n8n, click on **"Quarantine User Auto"** node
2. Check:
   - **Input**: Should show `{"user_id": 3}` (or the correct user ID)
   - **Output**: Should show the API response
   - **Status**: Should be "Success" (green) or "Error" (red)

### If the node shows an error:
- Check the error message
- Verify the URL: `http://host.docker.internal:8000/api/quarantine-user/`
- Verify the JSON body: `{"user_id": {{ $node["Webhook"].json.body.user_id }}}`

## Step 4: Check Workflow Execution Flow

The workflow should follow this path:
```
Webhook (receives incident)
  ↓
Send Telegram Alert
  ↓
If (file_hash exists?) → YES
  ↓
Download File
  ↓
Upload to VirusTotal
  ↓
Wait for Scan (5 seconds)
  ↓
Query VirusTotal (by file_hash)
  ↓
If1 (malicious > 0?) → YES
  ↓
Quarantine User Auto ← THIS SHOULD EXECUTE
  ↓
Send Security Alert
```

## Step 5: Common Issues and Fixes

### Issue 1: Query VirusTotal Returns Empty/Error
**Symptom**: Query VirusTotal node shows error or empty response

**Possible Causes**:
- File hash is wrong
- File not uploaded to VirusTotal yet
- VirusTotal API key issue

**Fix**:
- Check the "Upload to VirusTotal" node executed successfully
- Increase the "Wait for Scan" time (currently 5 seconds)
- Verify the file_hash in the webhook matches the uploaded file

### Issue 2: If1 Condition Always False
**Symptom**: If1 always goes to "false" branch (clean message)

**Possible Causes**:
- VirusTotal response structure is different
- Malicious count is 0 (file not detected)
- Condition syntax error

**Fix**:
- Check the actual VirusTotal response structure
- Use the improved condition: `{{ $json.data?.attributes?.last_analysis_stats?.malicious ?? 0 }}`
- Verify EICAR is actually detected (should show 50+ detections)

### Issue 3: Quarantine API Not Called
**Symptom**: Quarantine User Auto node doesn't execute

**Possible Causes**:
- If1 condition is false
- Workflow connection is broken
- Node is disabled

**Fix**:
- Check If1 output - should go to "true" branch
- Verify workflow connections
- Make sure all nodes are enabled

### Issue 4: Quarantine API Called But User Not Deactivated
**Symptom**: Quarantine API returns success but user is still active

**Possible Causes**:
- Wrong user_id sent
- Database update failed
- User object cached

**Fix**:
- Check the user_id in the API request
- Verify the API response shows `account_now_active: false`
- Check Django admin - user should be inactive
- Try refreshing the page

## Step 6: Manual Test

Test the quarantine API directly:

```bash
# Activate virtual environment
cd C:\Users\zhiwei.cheong\SIRTS_Project
.\venv\Scripts\Activate.ps1

# Test quarantine API
python -c "import requests; import json; response = requests.post('http://localhost:8000/api/quarantine-user/', json={'user_id': 3}, headers={'Content-Type': 'application/json'}); print(json.dumps(response.json(), indent=2))"
```

Expected response:
```json
{
  "status": "success",
  "message": "User ID 3 (hr) has been quarantined successfully",
  "user_id": 3,
  "username": "hr",
  "account_was_active": true,
  "account_now_active": false,
  "sessions_deleted": 1
}
```

## Step 7: Verify in Django Admin

1. Go to Django Admin → Users
2. Find the user who uploaded EICAR
3. Check the **"Active"** checkbox - it should be **UNCHECKED**
4. If still checked, the quarantine API was not called or failed

## Step 8: Check n8n Execution Logs

1. In n8n, go to **Executions** tab
2. Find the execution for the EICAR upload
3. Check each node:
   - **Webhook**: Should show `user_id` in the body
   - **Download File**: Should download successfully
   - **Upload to VirusTotal**: Should upload successfully
   - **Query VirusTotal**: Should return scan results with `malicious > 0`
   - **If1**: Should evaluate to `true`
   - **Quarantine User Auto**: Should call API and return success

## Quick Fix Checklist

- [ ] Workflow is **Active** (not Inactive)
- [ ] "Query VirusTotal" uses dynamic hash: `{{ $node["Webhook"].json.body.file_hash }}`
- [ ] "Quarantine User Auto" uses: `{{ $node["Webhook"].json.body.user_id }}`
- [ ] "If1" condition checks: `malicious > 0`
- [ ] All nodes have proper connections
- [ ] Django server is running
- [ ] n8n can reach Django at `http://host.docker.internal:8000`

## EICAR File Information

- **Purpose**: Standard test file for antivirus software
- **SHA256**: `131f95c51cc819465fa1797f6ccacf9d494daff26151609079e4e6d8c6c0d0b0`
- **Expected Detections**: 50+ antivirus engines should detect it
- **VirusTotal URL**: `https://www.virustotal.com/api/v3/files/131f95c51cc819465fa1797f6ccacf9d494daff26151609079e4e6d8c6c0d0b0`

## Still Not Working?

1. Check n8n execution logs for errors
2. Verify Django logs for API calls
3. Test quarantine API directly (see Step 6)
4. Check if user_id is correct in the webhook payload
5. Verify VirusTotal actually detects EICAR (check manually in browser)

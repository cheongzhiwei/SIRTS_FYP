# n8n Workflow Improvements Needed

## Issue Found: Hardcoded VirusTotal URL

In your workflow, the VirusTotal HTTP Request node has a hardcoded file hash:

```json
"url": "=https://www.virustotal.com/api/v3/files/275a021bbfb6489e54d471899f7db9d1663fc695ec2fe2a2c4538aabf651fd0f"
```

This should be dynamic to use the file hash from the webhook:

```json
"url": "=https://www.virustotal.com/api/v3/files/{{ $node[\"Webhook\"].json.body.file_hash }}"
```

## How to Fix in n8n

1. Open your workflow in n8n
2. Click on the **HTTP Request** node (the one that calls VirusTotal)
3. In the URL field, change from:
   ```
   https://www.virustotal.com/api/v3/files/275a021bbfb6489e54d471899f7db9d1663fc695ec2fe2a2c4538aabf651fd0f
   ```
   To:
   ```
   https://www.virustotal.com/api/v3/files/{{ $node["Webhook"].json.body.file_hash }}
   ```
4. Save the workflow

## Complete Workflow Checklist

Make sure your workflow has:

- [x] **Webhook** receives data with `reported_by_id` (✅ Fixed in Django code)
- [ ] **VirusTotal URL** uses dynamic `file_hash` (⚠️ Needs manual fix in n8n)
- [x] **Quarantine node** uses `reported_by_id` (✅ Already configured)
- [ ] **Error handling** - Consider adding error notifications

## Testing the Complete Flow

1. **Test User Setup**:
   - Create a test user
   - Log them in (creates a session)

2. **Test Incident**:
   - Report an incident with a file attachment
   - Use a known malicious file hash for testing (or let it scan normally)

3. **Check n8n Execution**:
   - Verify webhook received `reported_by_id`
   - Verify VirusTotal scan ran (if file_hash exists)
   - Verify quarantine node executed
   - Check quarantine node output for success/error

4. **Verify Quarantine**:
   ```bash
   python test_quarantine.py <user_id>
   ```

## Current Status

✅ **Fixed**: Django now sends `reported_by_id` in payload  
✅ **Fixed**: Quarantine API endpoint is working  
⚠️ **Needs Fix**: VirusTotal URL should be dynamic (manual fix in n8n)  
✅ **Working**: Quarantine node configuration looks correct  

## Next Steps

1. **Restart Django server** (to apply code changes)
2. **Update VirusTotal URL** in n8n workflow (manual)
3. **Test the complete flow** with a malicious file
4. **Verify quarantine** actually happened

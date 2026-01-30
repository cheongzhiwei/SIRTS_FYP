# Auto-Quarantine Fix Summary

## Problem Identified

The quarantine wasn't working because:
1. **Missing `reported_by_id` in payload**: The Django backend wasn't sending `reported_by_id` to n8n, so the workflow couldn't quarantine the user.
2. **Silent errors**: The workflow has `onError: continueRegularOutput`, so failures were hidden.

## Fixes Applied

### 1. ✅ Updated Django Backend (`incidents/views.py`)

Added `reported_by_id` and `user_id` to the payload sent to n8n:

```python
payload = {
    "ticket_id": incident.id,
    "title": incident.title,
    "department": incident.department,
    "laptop_serial": incident.laptop_serial,
    "reported_by": request.user.username,
    "reported_by_id": request.user.id,  # ← NEW: Added this
    "user_id": request.user.id,          # ← NEW: Added this
    "file_hash": file_hash if file_hash else "",
    "file_url": file_url
}
```

### 2. ✅ Your Workflow Configuration

Your workflow JSON shows the quarantine node is configured correctly:
- URL: `http://host.docker.internal:8000/api/quarantine-user/`
- Method: POST
- Body: `{"user_id": {{ $node["Webhook"].json.body.reported_by_id }}}`

**This should now work** because `reported_by_id` is now in the payload!

## Next Steps

### Step 1: Restart Django Server

After the code update, restart your Django server:

```bash
python manage.py runserver
```

### Step 2: Test the Quarantine API

Test if the API works:

```bash
python test_quarantine_api.py 1
```

### Step 3: Verify Payload in n8n

1. In n8n, check a recent webhook execution
2. Look at the Webhook node input
3. Verify `reported_by_id` is present in the body

### Step 4: Test with Malicious File

1. Log in as a test user
2. Report an incident with a file (use a known malicious hash for testing)
3. Check n8n execution
4. Verify the quarantine node executed
5. Check if user is actually quarantined

## Debugging

If it still doesn't work:

1. **Check n8n Execution Logs**:
   - Go to Executions tab
   - Find the execution
   - Click on "Quarantine User Auto" node
   - Check Input/Output/Error tabs

2. **Test API Directly**:
   ```bash
   curl -X POST http://localhost:8000/api/quarantine-user/ \
     -H "Content-Type: application/json" \
     -d '{"user_id": 1}'
   ```

3. **Check Django Logs**:
   - Look for API calls to `/api/quarantine-user/`
   - Check for any errors

4. **Verify User Status**:
   ```bash
   python manage.py shell
   ```
   ```python
   from django.contrib.auth.models import User
   user = User.objects.get(pk=1)  # Replace with test user ID
   print(f"Active: {user.is_active}")
   ```

## Workflow Flow

Your workflow should work like this:

```
User reports incident with file
  ↓
Django sends to n8n webhook (NOW INCLUDES reported_by_id)
  ↓
n8n sends Telegram alert
  ↓
n8n checks if file_hash exists
  ↓
If yes → VirusTotal scan
  ↓
If malicious > 0:
  ↓
  Quarantine User Auto (uses reported_by_id) ← Should work now!
  ↓
  Send security alert
```

## Important Notes

- The workflow has `onError: continueRegularOutput` which means errors are silently ignored
- To see errors, temporarily remove this setting or check execution logs
- Make sure `host.docker.internal:8000` is accessible from your n8n instance
- If using Docker, the host might be different

## Files Created

1. `test_quarantine_api.py` - Test the quarantine API directly
2. `WORKFLOW_DEBUG_GUIDE.md` - Detailed debugging guide
3. `test_quarantine.py` - Test quarantine functionality (from earlier)

Use these tools to verify everything is working!

# n8n Workflow Debugging Guide for Auto-Quarantine

## Issue: Quarantine Not Working Automatically

If the workflow shows it will auto-freeze but doesn't actually freeze the user, follow these steps:

## Step 1: Verify Payload Contains `reported_by_id`

The Django backend now sends `reported_by_id` in the payload. Verify this in n8n:

1. In n8n, go to your workflow
2. Click on the **Webhook** node
3. Check the execution history
4. Look at the input data - it should include:
   ```json
   {
     "body": {
       "ticket_id": 123,
       "title": "...",
       "reported_by": "username",
       "reported_by_id": 1,  // ← This should be present
       "user_id": 1,         // ← This too
       "file_hash": "..."
     }
   }
   ```

## Step 2: Check Quarantine Node Configuration

In your workflow, the **Quarantine User Auto** node should have:

- **URL**: `http://host.docker.internal:8000/api/quarantine-user/`
- **Method**: POST
- **Body**: JSON
- **JSON Body**: 
  ```json
  {
    "user_id": {{ $node["Webhook"].json.body.reported_by_id }}
  }
  ```

**Important**: Make sure `reported_by_id` is available. If not, you can also use:
```json
{
  "user_id": {{ $node["Webhook"].json.body.user_id }}
}
```

## Step 3: Test the Quarantine API Directly

Run the test script to verify the API works:

```bash
python test_quarantine_api.py 1
```

Or with custom URL:
```bash
python test_quarantine_api.py 1 http://host.docker.internal:8000
```

This will show you:
- If the API is accessible
- If the quarantine is working
- How many sessions were deleted
- Any error messages

## Step 4: Check n8n Execution Logs

1. In n8n, go to **Executions** tab
2. Find the execution where malware was detected
3. Click on the **Quarantine User Auto** node
4. Check:
   - **Input**: Should show the user_id being sent
   - **Output**: Should show the API response
   - **Error**: Check if there are any errors (even with `onError: continueRegularOutput`)

## Step 5: Common Issues and Fixes

### Issue 1: `reported_by_id` is undefined

**Symptom**: Quarantine node shows error or empty user_id

**Fix**: 
- Make sure Django is sending `reported_by_id` in the payload (already fixed in code)
- Restart Django server after the code update
- Check webhook input data in n8n

### Issue 2: API Connection Error

**Symptom**: Quarantine node shows connection error

**Fixes**:
- Verify Django server is running
- Check if `host.docker.internal:8000` is accessible from n8n
- Try using `localhost:8000` or your actual server IP
- Check firewall settings

### Issue 3: API Returns Error

**Symptom**: API responds but with error status

**Check**:
- User ID exists in database
- User is not already quarantined
- Check API response for specific error message

### Issue 4: Silent Failure (onError: continueRegularOutput)

**Symptom**: Workflow continues but quarantine doesn't happen

**Fix**: 
- Temporarily remove `onError: continueRegularOutput` to see errors
- Or add a "Send Error Message" node after quarantine to catch errors
- Check execution logs for the quarantine node

## Step 6: Add Error Handling to Workflow

To better debug, you can add error handling:

1. After **Quarantine User Auto** node, add an **IF** node
2. Check if `{{ $json.status }} === 'success'`
3. If false, send an error notification to Telegram

Or modify the quarantine node:
- Remove `onError: continueRegularOutput` temporarily
- This will stop the workflow on error so you can see what's wrong
- Once fixed, add it back

## Step 7: Verify Quarantine Actually Happened

After the workflow runs:

1. **Check User Status**:
   ```bash
   python manage.py shell
   ```
   ```python
   from django.contrib.auth.models import User
   user = User.objects.get(pk=1)  # Replace with actual user ID
   print(f"User active: {user.is_active}")
   ```

2. **Check Sessions**:
   ```python
   from django.contrib.sessions.models import Session
   from django.utils import timezone
   
   sessions = Session.objects.filter(expire_date__gte=timezone.now())
   for session in sessions:
       try:
           data = session.get_decoded()
           if str(user.pk) == str(data.get('_auth_user_id', '')):
               print(f"Active session found: {session.session_key}")
       except:
           pass
   ```

## Updated Workflow Configuration

Make sure your workflow has this flow:

```
Webhook
  ↓
Send Alert (Telegram)
  ↓
If (file_hash exists?)
  ├─ Yes → VirusTotal Scan
  │         ↓
  │       If1 (malicious > 0?)
  │         ├─ Yes → Quarantine User Auto ← Check this node!
  │         │         ↓
  │         │       Send Security Alert
  │         └─ No → Send Clean Message
  └─ No → Send No Attachment Message
```

## Testing Checklist

- [ ] Django server is running
- [ ] Payload includes `reported_by_id` (check webhook input)
- [ ] Quarantine API is accessible (test with script)
- [ ] Quarantine node has correct URL
- [ ] Quarantine node has correct JSON body format
- [ ] No errors in n8n execution logs
- [ ] User is actually deactivated after workflow runs
- [ ] Sessions are deleted after workflow runs

## Quick Test

1. Create a test user and log them in
2. Report an incident with a known malicious file hash
3. Check n8n execution
4. Verify user is quarantined:
   ```bash
   python test_quarantine.py <user_id>
   ```

## Still Not Working?

1. Check Django logs for API calls
2. Check n8n execution details
3. Test quarantine API directly with curl:
   ```bash
   curl -X POST http://localhost:8000/api/quarantine-user/ \
     -H "Content-Type: application/json" \
     -d '{"user_id": 1}'
   ```
4. Verify the user_id in the database matches what's being sent

# Fix: "The resource you are requesting could not be found" in n8n

## Problem
n8n workflow returns "The resource you are requesting could not be found" when trying to download files from Django.

## Root Cause
The file URL was being generated using `request.build_absolute_uri()` which creates URLs like:
- `http://127.0.0.1:8000/media/incident_attachments/file.ext`
- `http://localhost:8000/media/incident_attachments/file.ext`

These URLs are not accessible from n8n running in Docker because:
1. Docker containers can't access `localhost` or `127.0.0.1` from the host
2. Even with `host.docker.internal`, the URL might not be accessible
3. n8n needs a publicly accessible URL (like ngrok)

## Solution
Updated Django to use the ngrok URL (same as webhook URL) for file URLs:

1. **Added `EXTERNAL_BASE_URL` setting** in `settings.py`:
   ```python
   EXTERNAL_BASE_URL = 'https://backmost-blowiest-arnold.ngrok-free.dev'
   ```

2. **Updated file URL generation** in `views.py`:
   - Uses `EXTERNAL_BASE_URL` from settings
   - Falls back to request-based URL if setting is not available
   - Includes error handling

3. **Updated `ALLOWED_HOSTS`** to include ngrok domain

## Testing

### Step 1: Verify Django is accessible via ngrok
```bash
# Test if ngrok is forwarding correctly
curl https://backmost-blowiest-arnold.ngrok-free.dev/admin/
```

### Step 2: Test file URL generation
1. Submit an incident with a file attachment
2. Check the n8n webhook payload - it should include:
   ```json
   {
     "file_url": "https://backmost-blowiest-arnold.ngrok-free.dev/media/incident_attachments/filename.ext",
     "file_hash": "d4eb835c6d9e60ed18e9edc62d1e556b84398cd48adb6374c870d0c330fcffdf"
   }
   ```

### Step 3: Test file download from n8n
In n8n, add an HTTP Request node to test:
- **Method**: GET
- **URL**: `={{ $json.body.file_url }}`
- **Headers**: 
  - `ngrok-skip-browser-warning: true` (if using ngrok free tier)

### Step 4: Verify file exists
Check Django media directory:
```bash
ls -la media/incident_attachments/
```

## Important Notes

### ngrok Free Tier Headers
If you're using ngrok free tier, you may need to add headers to bypass the browser warning:
- Header: `ngrok-skip-browser-warning: true`
- Or configure ngrok to skip browser warning: `ngrok http 8000 --host-header="localhost:8000"`

### Updating ngrok URL
When your ngrok URL changes:
1. Update `EXTERNAL_BASE_URL` in `settings.py`
2. Restart Django server
3. Update n8n webhook URL if needed

### Docker Network Access
If n8n is running in Docker and Django is on host:
- Use `host.docker.internal:8000` for direct access (if file_url is empty)
- Or use ngrok/public URL (recommended)

### File Permissions
Make sure Django can write to `media/incident_attachments/`:
```bash
mkdir -p media/incident_attachments
chmod 755 media/incident_attachments
```

## Troubleshooting

### Issue: Still getting 404
1. Check if ngrok is running: `curl https://backmost-blowiest-arnold.ngrok-free.dev/`
2. Check Django logs for file access attempts
3. Verify `EXTERNAL_BASE_URL` matches your ngrok URL
4. Check `ALLOWED_HOSTS` includes ngrok domain

### Issue: File URL is empty
1. Check if file was actually uploaded
2. Check Django logs for errors during file save
3. Verify `incident.attachment` exists before building URL

### Issue: ngrok browser warning
Add header in n8n HTTP Request:
- `ngrok-skip-browser-warning: true`

### Issue: CORS errors
If accessing from browser, add CORS headers in Django (if needed):
```python
# In settings.py (if using django-cors-headers)
CORS_ALLOWED_ORIGINS = [
    "https://backmost-blowiest-arnold.ngrok-free.dev",
]
```

## Current Configuration

- **Django URL**: `http://127.0.0.1:8000` (local)
- **ngrok URL**: `https://backmost-blowiest-arnold.ngrok-free.dev`
- **File URLs**: Now use ngrok URL for n8n access
- **Webhook URL**: Uses ngrok URL

## Next Steps

1. ✅ File URLs now use ngrok URL
2. ✅ Added error handling
3. ✅ Made URL configurable via settings
4. ⏭️ Test file download in n8n workflow
5. ⏭️ Update n8n workflow to handle file downloads properly

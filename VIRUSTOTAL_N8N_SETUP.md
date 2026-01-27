# VirusTotal Integration Setup Guide for n8n

## Problem
The current n8n workflow tries to query VirusTotal using only the file hash, but VirusTotal returns "File not found" because the file hasn't been uploaded to VirusTotal yet.

## Solution
We need to upload the file to VirusTotal first, then query the scan results.

## Updated n8n Workflow Steps

### Current Flow:
1. Webhook receives incident data with `file_hash`
2. HTTP Request tries to GET `/api/v3/files/{hash}` → **Fails because file not uploaded**

### Updated Flow:
1. Webhook receives incident data with `file_hash` and `file_url`
2. **IF** `file_url` exists and is not empty:
   - Download file from `file_url`
   - Upload file to VirusTotal (POST `/api/v3/files`)
   - Wait for scan completion (optional: poll status)
   - Query scan results (GET `/api/v3/files/{hash}`)
3. **ELSE** (no file):
   - Skip VirusTotal scanning
   - Continue with Telegram notification

## n8n Workflow Configuration

### Step 1: Add IF Node (Check if file exists)
After the Webhook node, add an IF node:
- **Condition**: `{{ $json.body.file_url }}` is not empty
- **Operation**: Check if `file_url` exists

### Step 2: Download File (HTTP Request)
- **Method**: GET
- **URL**: `={{ $json.body.file_url }}`
- **Response Format**: File
- **Output Property**: `fileData`

### Step 3: Upload to VirusTotal (HTTP Request)
- **Method**: POST
- **URL**: `https://www.virustotal.com/api/v3/files`
- **Authentication**: Header Auth
  - **Header Name**: `x-apikey`
  - **Header Value**: `[Your VirusTotal API Key]`
- **Body Type**: Form-Data or Binary
- **Body**:
  - **Key**: `file`
  - **Value**: `={{ $json.fileData }}` (from previous step)

### Step 4: Extract Analysis ID (Function/Set Node)
After upload, VirusTotal returns an `analysis_id`. Extract it:
```javascript
// In a Function node or Set node
return {
  analysis_id: $json.data.id,
  file_hash: $json.body.file_hash
};
```

### Step 5: Query Scan Results (HTTP Request)
- **Method**: GET
- **URL**: `=https://www.virustotal.com/api/v3/files/{{ $json.body.file_hash }}`
- **Authentication**: Header Auth
  - **Header Name**: `x-apikey`
  - **Header Value**: `[Your VirusTotal API Key]`
- **Options**: 
  - Add retry logic (scan may take a few seconds)
  - Or use `/api/v3/analyses/{analysis_id}` endpoint

### Step 6: Process Results (Optional)
Add a node to format and send VirusTotal results:
- Extract detection count
- Extract threat names
- Send alert if threats found

## Alternative: Use Analysis Endpoint

Instead of querying by hash immediately, you can use the analysis endpoint:

1. **Upload file** → Get `analysis_id`
2. **Poll analysis status**: `GET /api/v3/analyses/{analysis_id}`
3. **When status = "completed"**: Get results

## Example n8n Workflow JSON Structure

```json
{
  "nodes": [
    {
      "name": "Webhook",
      "type": "n8n-nodes-base.webhook"
    },
    {
      "name": "IF File Exists",
      "type": "n8n-nodes-base.if",
      "parameters": {
        "conditions": {
          "string": [{
            "value1": "={{ $json.body.file_url }}",
            "operation": "isNotEmpty"
          }]
        }
      }
    },
    {
      "name": "Download File",
      "type": "n8n-nodes-base.httpRequest",
      "parameters": {
        "method": "GET",
        "url": "={{ $json.body.file_url }}",
        "options": {
          "response": {
            "response": {
              "responseFormat": "file"
            }
          }
        }
      }
    },
    {
      "name": "Upload to VirusTotal",
      "type": "n8n-nodes-base.httpRequest",
      "parameters": {
        "method": "POST",
        "url": "https://www.virustotal.com/api/v3/files",
        "authentication": "genericCredentialType",
        "genericAuthType": "httpHeaderAuth",
        "sendBody": true,
        "bodyParameters": {
          "parameters": [{
            "name": "file",
            "value": "={{ $json.data }}"
          }]
        }
      }
    },
    {
      "name": "Get Scan Results",
      "type": "n8n-nodes-base.httpRequest",
      "parameters": {
        "method": "GET",
        "url": "=https://www.virustotal.com/api/v3/files/{{ $json.body.file_hash }}",
        "authentication": "genericCredentialType",
        "genericAuthType": "httpHeaderAuth"
      }
    }
  ]
}
```

## Important Notes

1. **API Rate Limits**: VirusTotal has rate limits. Consider adding delays between requests.

2. **File Size Limits**: VirusTotal accepts files up to 650MB. Larger files may fail.

3. **Scan Time**: Scans can take 10-60 seconds. Consider:
   - Using webhooks for completion notifications
   - Polling the analysis endpoint
   - Or querying by hash after a delay

4. **Error Handling**: Add error handling nodes to catch:
   - File download failures
   - Upload failures
   - Rate limit errors

5. **Security**: Make sure your Django server is accessible from n8n (consider ngrok or similar for local development).

## Testing

1. Submit an incident with a file attachment
2. Check n8n execution logs
3. Verify file is downloaded
4. Verify file is uploaded to VirusTotal
5. Verify scan results are retrieved

## Current Django Implementation

Django now sends:
- `file_hash`: SHA256 hash of the file
- `file_url`: Full URL to download the file (e.g., `http://127.0.0.1:8000/media/incident_attachments/filename.ext`)

Make sure your Django server is accessible from n8n. If running locally, use ngrok or similar tunneling service.

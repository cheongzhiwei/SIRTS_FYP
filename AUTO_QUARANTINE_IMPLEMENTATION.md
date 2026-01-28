# Auto-Quarantine Implementation for Malware Detection

## Overview
This implementation automatically quarantines users (kills sessions and deactivates accounts) when malware is detected in uploaded files during incident reporting.

## Changes Made

### 1. Django Backend Changes

#### New API Endpoint: `/api/quarantine-user/`
- **Location**: `incidents/views.py`
- **Method**: POST
- **Purpose**: Automatically quarantine a user when called by n8n workflow
- **Request Body**:
  ```json
  {
    "user_id": 123
  }
  ```
- **Response**:
  ```json
  {
    "status": "success",
    "message": "User ID 123 (username) has been quarantined successfully",
    "user_id": 123,
    "username": "username",
    "sessions_deleted": 2
  }
  ```

#### Updated Webhook Endpoint
- **Location**: `incidents/views.py` - `n8n_webhook_new_incident()`
- **Change**: Now returns `reported_by_id`, `reported_by`, and `user_id` in the response
- **Purpose**: Allows n8n workflow to access the user ID for automatic quarantine

#### URL Configuration
- **Location**: `incidents/urls.py`
- **Added**: `path('api/quarantine-user/', views.quarantine_user_api, name='quarantine_user_api')`

### 2. n8n Workflow Changes

#### Modified Workflow File
- **Location**: `c:\Users\zhiwei.cheong\Downloads\user freeze_auto_quarantine.json`
- **Key Changes**:
  1. Added new HTTP Request node: "Quarantine User Auto"
  2. Updated flow: When malware is detected (If1 → true), automatically calls quarantine API
  3. Updated Telegram notification to indicate automatic quarantine
  4. Fixed VirusTotal URL to use dynamic file hash from webhook

#### Workflow Flow
```
Webhook → Send Alert → Check File Hash
                              ↓
                         VirusTotal Scan
                              ↓
                         Check if Malicious
                              ↓
                    ┌─────────┴─────────┐
                    │                   │
              Malicious > 0        Malicious = 0
                    │                   │
         Quarantine User Auto    Send Clean Message
                    │
         Send Security Alert (with quarantine notice)
```

## How It Works

1. **Incident Creation**: User reports incident with file attachment
2. **File Hash**: System calculates SHA256 hash of uploaded file
3. **VirusTotal Scan**: n8n workflow sends hash to VirusTotal API
4. **Malware Detection**: If malicious detections > 0:
   - **Automatic Action**: n8n calls `/api/quarantine-user/` with `reported_by_id`
   - **Backend Action**: 
     - Deactivates user account (`user.is_active = False`)
     - Kills all active sessions for that user
   - **Notification**: Sends Telegram alert indicating automatic quarantine
5. **Clean File**: If no threats detected, sends clean scan notification

## API Endpoints

### Quarantine User
```
POST http://host.docker.internal:8000/api/quarantine-user/
Content-Type: application/json

{
  "user_id": 123
}
```

### Update Ticket (existing)
```
POST http://host.docker.internal:8000/api/update-ticket/
Content-Type: application/json

{
  "ticket_id": 456
}
```

## Testing

1. **Test Quarantine API**:
   ```bash
   curl -X POST http://localhost:8000/api/quarantine-user/ \
     -H "Content-Type: application/json" \
     -d '{"user_id": 1}'
   ```

2. **Test with n8n**:
   - Import the updated workflow JSON file
   - Ensure webhook receives `reported_by_id` in the body
   - Test with a file that has known malware hash

## Security Considerations

- The quarantine endpoint is CSRF-exempt (required for n8n webhooks)
- Only accepts POST requests
- Validates user_id exists before quarantining
- Returns detailed error messages for debugging
- Continues workflow execution even if quarantine fails (onError: continueRegularOutput)

## Notes

- The workflow uses `host.docker.internal:8000` - adjust if your Django server runs on a different host/port
- The VirusTotal URL in the original workflow was hardcoded - updated to use dynamic hash from webhook
- The quarantine button in Telegram is now informational only (shows "Acknowledged" instead of "Quarantine User") since quarantine happens automatically

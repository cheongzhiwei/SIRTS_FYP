# AI Ticket Classifier - n8n Integration Guide

## Problem Solved
The n8n Python Code node requires Python 3 to be installed in the n8n environment, which is not available in internal mode. This solution provides a Django API endpoint that n8n can call via HTTP instead.

## Solution Overview

Instead of running Python code directly in n8n, we've created:
1. **Django API Endpoint** (`/api/classify-ticket/`) - Classifies tickets using AI
2. **Django API Endpoint** (`/api/update-ticket-category/`) - Updates the ticket category in the database

## n8n Workflow Update Instructions

### Step 1: Replace Python Code Node with HTTP Request Node

**Remove:**
- The "Code in Python" node that contains the sklearn classification code

**Add:**
- An "HTTP Request" node to call the Django classification API

### Step 2: Configure the HTTP Request Node

**Node Name:** `Classify Ticket`

**Settings:**
- **Method:** `POST`
- **URL:** `http://host.docker.internal:8000/api/classify-ticket/`
- **Send Body:** `true`
- **Specify Body:** `json`
- **JSON Body:**
```json
{
  "title": "{{ $json.body.title }}",
  "description": "{{ $json.body.description }}"
}
```

**Alternative (using ticket_id):**
```json
{
  "ticket_id": {{ $json.body.ticket_id }}
}
```

### Step 3: Update the Category Update Node

The existing "HTTP Request" node that updates the category should be updated to use proper JSON:

**Node Name:** `Update Ticket Category` (or `HTTP Request`)

**Settings:**
- **Method:** `POST`
- **URL:** `http://host.docker.internal:8000/api/update-ticket-category/`
- **Send Body:** `true`
- **Specify Body:** `json`
- **JSON Body:**
```json
{
  "ticket_id": {{ $json.body.ticket_id }},
  "category": "{{ $node[\"Classify Ticket\"].json.predicted_category }}"
}
```

### Step 4: Update Node Connections

**New Flow:**
1. Webhook → Classify Ticket (HTTP Request)
2. Classify Ticket → Update Ticket Category (HTTP Request)
3. Update Ticket Category → If (file hash check)
4. If → (rest of workflow)

## API Endpoints

### 1. Classify Ticket API
**Endpoint:** `POST /api/classify-ticket/`

**Request Body:**
```json
{
  "title": "laptop screen is flickering",
  "description": "The screen keeps flickering when I use it"
}
```

**OR:**
```json
{
  "ticket_id": 123
}
```

**Response:**
```json
{
  "status": "success",
  "predicted_category": "Hardware",
  "confidence": 0.85,
  "title": "laptop screen is flickering",
  "description": "The screen keeps flickering...",
  "ticket_id": null
}
```

### 2. Update Ticket Category API
**Endpoint:** `POST /api/update-ticket-category/`

**Request Body:**
```json
{
  "ticket_id": 123,
  "category": "Hardware"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Ticket #123 category updated successfully",
  "ticket_id": 123,
  "old_category": null,
  "new_category": "Hardware"
}
```

## Complete n8n Workflow Structure

```
Webhook (new-incident)
  ↓
Classify Ticket (HTTP Request) → /api/classify-ticket/
  ↓
Update Ticket Category (HTTP Request) → /api/update-ticket-category/
  ↓
If (file_hash check)
  ├─ True → Download File → Upload to VirusTotal → Wait → Query VirusTotal → If (malicious check)
  │                                                                    ├─ True → Quarantine User → Send Alert
  │                                                                    └─ False → Send Clean Message
  └─ False → Send No Attachment Message
```

## Testing

### Test Classification API:
```bash
curl -X POST http://localhost:8000/api/classify-ticket/ \
  -H "Content-Type: application/json" \
  -d '{"title": "laptop screen flickering", "description": "screen keeps flickering"}'
```

### Test Update Category API:
```bash
curl -X POST http://localhost:8000/api/update-ticket-category/ \
  -H "Content-Type: application/json" \
  -d '{"ticket_id": 1, "category": "Hardware"}'
```

## Benefits

1. ✅ **No Python Required in n8n** - All Python code runs in Django
2. ✅ **Better Performance** - Model is loaded once and reused
3. ✅ **Easier Maintenance** - Classification logic centralized in Django
4. ✅ **Better Error Handling** - Proper HTTP status codes and error messages
5. ✅ **Reusable** - Can be called from anywhere, not just n8n

## Troubleshooting

### Error: "Failed to import classifier"
- Make sure `scikit-learn`, `pandas`, and `numpy` are installed in your Django virtual environment:
  ```bash
  pip install scikit-learn pandas numpy
  ```

### Error: "Connection refused"
- Make sure Django server is running
- Check that `host.docker.internal` resolves correctly (or use `localhost` if n8n is on the same machine)

### Classification returns "Other"
- The model might need more training data
- Check that title and description are being passed correctly
- Review the training data in `ticket_classifier.py`

## Next Steps

1. Update your n8n workflow as described above
2. Test with a sample ticket
3. Monitor the classification accuracy
4. Add more training data to `ticket_classifier.py` if needed for better accuracy

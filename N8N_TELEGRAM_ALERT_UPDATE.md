# Telegram Alert Update - AI Classification Display

## Changes Made

The Telegram alert message has been updated to include:

1. **Description** - Shows the full incident description
2. **AI Category** - Displays the predicted category (Hardware/Software/Network/Account/Other)
3. **Confidence Score** - Shows the AI's confidence percentage
4. **Better Formatting** - Added emojis and clearer structure

## Updated Telegram Message Format

```
🚨 SIRTS Alert

📋 Issue: [Title]
📝 Description: [Full description]
🎫 Ticket ID: #[Ticket ID]
🤖 AI Category: [Category] ([Confidence]% confidence)
💻 Hardware SN: [Serial Number]
🏢 Department: [Department]
👤 Reported By: [Username]
🆔 User ID: [User ID]

Please acknowledge [Button]
```

## What Changed in the Workflow

### Before:
- Only showed basic ticket info
- No AI classification visible
- No description shown

### After:
- Shows full description
- Displays AI-predicted category
- Shows confidence score (0-100%)
- Better visual formatting with emojis
- Fallback values (N/A) if data is missing

## Node References Used

The Telegram message now correctly references:
- `$node["Webhook"]` - Original webhook data (title, description, ticket_id, etc.)
- `$node["Classify Ticket"]` - AI classification results (predicted_category, confidence)

## Testing

1. Create a new incident in Django
2. Check Telegram for the alert
3. Verify you see:
   - ✅ Full description
   - ✅ AI Category (Hardware/Software/Network/Account/Other)
   - ✅ Confidence percentage
   - ✅ All other ticket details

## Troubleshooting

If the AI category shows "Pending" or confidence is 0%:
- Check that the "Classify Ticket" node executed successfully
- Verify the API endpoint `/api/classify-ticket/` is accessible
- Check n8n execution logs for errors

If description is missing:
- Verify Django is sending `description` in the webhook payload (already fixed in views.py)
- Check that the incident has a description field filled

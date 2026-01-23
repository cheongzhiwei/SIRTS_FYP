# Telegram IT Acknowledgment Setup Guide

This guide explains how to set up the Telegram integration for IT acknowledgment of incidents.

## Overview

When a new incident is reported, IT receives a Telegram message with two buttons:
1. **✅ Acknowledge** - Marks the ticket as acknowledged by IT
2. **💬 Leave Message** - Allows IT to leave a status message (e.g., "Waiting for parts", "Cannot finish today")

## Setup Steps

### 1. Update n8n Workflow

The main workflow (`My workflow.json`) sends Telegram messages with inline keyboard buttons. The callback_data format is:
- `ack_<ticket_id>` for acknowledge button
- `msg_<ticket_id>` for leave message button

**Note:** In n8n, you may need to use a Code node or Function node to construct the callback_data properly if expressions don't work directly. Example:

```javascript
// In a Code node before the Telegram node
const ticketId = $input.item.json.body.ticket_id;
return {
  json: {
    ...$input.item.json,
    callback_data_ack: `ack_${ticketId}`,
    callback_data_msg: `msg_${ticketId}`
  }
};
```

Then use `{{ $json.callback_data_ack }}` in the Telegram node.

### 2. Set Up Telegram Callback Handler

Import the `telegram_callback_workflow.json` into n8n. This workflow:
- Listens for Telegram callback queries
- Routes "ack_" callbacks to the acknowledge endpoint
- Routes "msg_" callbacks to prompt IT for a message

### 3. Configure Telegram Bot Webhook

1. In n8n, activate the "Telegram Callback Handler" workflow
2. Make sure your Telegram bot token is configured in n8n credentials
3. The workflow will automatically set up the webhook with Telegram

### 4. Update Django Settings (if needed)

If your Django server is not on localhost:8000, update the webhook URLs in:
- `telegram_callback_workflow.json` - Update the HTTP Request node URLs
- The base URL should match your Django server URL

### 5. Run Migrations

After updating the code, run:
```bash
python manage.py migrate
```

## How It Works

### Acknowledge Flow
1. IT clicks "✅ Acknowledge" button in Telegram
2. Telegram sends callback query to n8n
3. n8n routes to Django webhook: `/webhook/telegram/acknowledge/<ticket_id>/`
4. Django updates the incident:
   - Sets `it_acknowledged = True`
   - Sets `it_acknowledged_at` to current time
   - Sets `it_acknowledged_by` to IT user
   - Changes status to "In Progress" if it was "Open"
5. n8n sends confirmation message back to Telegram

### Leave Message Flow
1. IT clicks "💬 Leave Message" button in Telegram
2. Telegram sends callback query to n8n
3. n8n prompts IT to send a message
4. IT sends their status message (e.g., "Waiting for parts to arrive")
5. n8n captures the message and sends to Django webhook: `/webhook/telegram/message/<ticket_id>/`
6. Django updates the incident:
   - Appends message to `it_status_message` field
   - Marks as acknowledged if not already
   - Updates status to "In Progress" if needed

## Dashboard Display

### Admin Dashboard
- Shows "IT Status" column with acknowledgment status
- Displays IT messages if available
- Shows who acknowledged and when

### User Dashboard (home.html)
- Shows IT acknowledgment status for open tickets
- Displays IT status messages in ticket details modal
- Users can see if IT is waiting for parts or has other updates

## Testing

1. Create a test incident
2. Check Telegram for the alert message with buttons
3. Click "Acknowledge" - verify it updates in the dashboard
4. Click "Leave Message" - send a test message, verify it appears in dashboard

## Troubleshooting

### Buttons not appearing
- Check that `reply_markup` is properly formatted in n8n
- Verify callback_data is constructed correctly (may need Code node)

### Callbacks not working
- Ensure "Telegram Callback Handler" workflow is active in n8n
- Check Telegram bot webhook is set up correctly
- Verify Django webhook URLs are accessible

### Messages not updating
- Check Django logs for webhook errors
- Verify database migrations have been run
- Check that IT user exists in Django (first staff user is used by default)

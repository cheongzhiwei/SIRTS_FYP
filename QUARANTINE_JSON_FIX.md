# Fix for "JSON parameter needs to be valid JSON" Error

## Problem
The "Quarantine User Auto" node is showing error: "JSON parameter needs to be valid JSON"

## Root Cause
The `jsonBody` parameter in n8n needs to be properly formatted. When using expressions in JSON, n8n requires specific syntax.

## Solution

In n8n, when using `specifyBody: "json"`, you have two options:

### Option 1: Use Object Expression (Recommended)
Change the `jsonBody` to use n8n's object expression syntax:

```json
"jsonBody": "={{ { user_id: $node[\"Webhook\"].json.body.user_id } }}"
```

This creates a JavaScript object that n8n automatically converts to JSON.

### Option 2: Use String with Proper Formatting
If Option 1 doesn't work, use a properly formatted JSON string:

```json
"jsonBody": "={{ '{\"user_id\":' + $node[\"Webhook\"].json.body.user_id + '}' }}"
```

### Option 3: Use bodyParameters (Alternative)
Instead of `jsonBody`, you can use `bodyParameters`:

```json
"specifyBody": "keypair",
"bodyParameters": {
  "parameters": [
    {
      "name": "user_id",
      "value": "={{ $node[\"Webhook\"].json.body.user_id }}"
    }
  ]
}
```

But this sends as form data, not JSON, so you'd need to change the Content-Type or use a different approach.

## Current Fix Applied

I've updated the workflow to use Option 1:
```json
"jsonBody": "={{ { user_id: $node[\"Webhook\"].json.body.user_id } }}"
```

## Testing

1. Import the updated workflow
2. Test with EICAR.txt
3. Check the "Quarantine User Auto" node - it should no longer show the JSON error
4. Verify the API is called with: `{"user_id": 3}` (or the correct user ID)

## If Still Not Working

If you still get the error, try:

1. **Check the user_id value**: Make sure `$node["Webhook"].json.body.user_id` actually has a value
   - In n8n, click on the "Webhook" node
   - Check the output - verify `user_id` exists in the body

2. **Use a Function node** (most reliable):
   - Add a Function node before "Quarantine User Auto"
   - Code:
     ```javascript
     return {
       json: {
         user_id: $node["Webhook"].json.body.user_id
       }
     };
     ```
   - Then in "Quarantine User Auto", use: `={{ $json.user_id }}` or reference the function node output

3. **Check n8n version**: Some older versions of n8n have different expression syntax

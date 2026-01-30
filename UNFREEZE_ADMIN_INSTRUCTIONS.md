# Instructions to Unfreeze Admin (User ID 2)

## Quick Fix

Run this command in your terminal (make sure your virtual environment is activated):

```bash
python manage.py unfreeze_user 2
```

Or if you prefer using Python directly:

```bash
python manage.py shell
```

Then in the shell:
```python
from django.contrib.auth.models import User
admin = User.objects.get(pk=2)
admin.is_active = True
admin.save()
print(f"Admin {admin.username} has been unfrozen")
exit()
```

## Verify the Fix

After unfreezing, verify it worked:

```bash
python manage.py shell
```

```python
from django.contrib.auth.models import User
admin = User.objects.get(pk=2)
print(f"Admin active: {admin.is_active}")  # Should be True
```

## Understanding the Issue

The quarantine should freeze the **reported user** (the user who reported the incident), not the admin.

The code uses `request.user.id` which is the logged-in user who submitted the incident report. This should be correct.

## Check What User ID is Being Sent

To verify the correct user_id is being sent to n8n:

1. Check the n8n webhook execution
2. Look at the Webhook node input
3. Verify `reported_by_id` matches the user who reported the incident
4. Check the Quarantine User Auto node to see what `user_id` it's sending

## If Wrong User is Being Quarantined

If the wrong user is being quarantined, check:

1. **n8n Workflow**: Verify the quarantine node uses:
   ```json
   {
     "user_id": {{ $node["Webhook"].json.body.reported_by_id }}
   }
   ```

2. **Django Payload**: The payload should include:
   ```python
   "reported_by_id": request.user.id  # This is the logged-in user
   ```

3. **Test**: Create a test incident as a regular user (not admin) and verify it quarantines that user, not the admin.

## Prevention

To prevent accidentally freezing the wrong user:

- Always test with a non-admin test user
- Check the user_id in n8n execution logs before the quarantine happens
- Consider adding a check to prevent freezing admin users (optional)

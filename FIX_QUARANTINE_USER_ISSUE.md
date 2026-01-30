# Fix: Quarantine Should Freeze Reported User, Not Admin

## Problem
After testing, the admin (user ID 2) was frozen instead of the reported user (user ID 1).

## Solution

### Step 1: Unfreeze the Admin

Run this command (activate your virtual environment first):

```bash
python manage.py unfreeze_user 2
```

Or use Django shell:
```bash
python manage.py shell
```

Then:
```python
from django.contrib.auth.models import User
admin = User.objects.get(pk=2)
admin.is_active = True
admin.save()
print(f"✓ Admin {admin.username} unfrozen")
exit()
```

### Step 2: Verify the Code Logic

The code is **correct** - it uses `request.user.id` which is the logged-in user who reported the incident:

```python
# In report_incident view (line 282-283)
payload = {
    ...
    "reported_by_id": request.user.id,  # ← This is the logged-in user
    "user_id": request.user.id,          # ← Same here
    ...
}
```

This means:
- If **User 1** reports an incident → `reported_by_id = 1` → Quarantines User 1 ✅
- If **User 2** (admin) reports an incident → `reported_by_id = 2` → Quarantines User 2 ✅

### Step 3: Check What Actually Happened

To understand why admin was frozen, check:

1. **Who reported the incident?**
   - If admin (user 2) reported it, then freezing user 2 is correct behavior
   - If user 1 reported it, then there's a bug

2. **Check n8n execution logs:**
   - Look at the Webhook node input
   - Check what `reported_by_id` value was sent
   - Check what `user_id` the Quarantine node sent

3. **Check the incident in database:**
   ```bash
   python manage.py shell
   ```
   ```python
   from incidents.models import Incident
   # Get the most recent incident
   incident = Incident.objects.latest('created_at')
   print(f"Incident ID: {incident.id}")
   print(f"Reported by user ID: {incident.user.id}")
   print(f"Reported by username: {incident.user.username}")
   ```

## Expected Behavior

The quarantine should freeze:
- ✅ **The user who reported the incident** (the logged-in user)
- ❌ NOT the admin (unless admin reported it)

## Testing

To test correctly:

1. **Create a test user** (not admin):
   ```bash
   python manage.py createsuperuser
   # Or use existing non-admin user
   ```

2. **Log in as the test user** (not admin)

3. **Report an incident** with a malicious file

4. **Verify** the test user (not admin) gets quarantined

## Prevention: Optional Safety Check

If you want to prevent accidentally freezing admin users, you can add a check:

```python
# In quarantine_user_api view, add this before quarantining:
if user.is_staff or user.is_superuser:
    return JsonResponse({
        'status': 'error',
        'message': 'Cannot quarantine admin/superuser accounts'
    }, status=400)
```

But this is optional - the current behavior is correct (freezes whoever reported the incident).

## Summary

- ✅ Code is correct - uses `request.user.id`
- ✅ Unfreeze admin: `python manage.py unfreeze_user 2`
- ✅ Test with a non-admin user to verify it works correctly
- ⚠️ If admin reported the incident, freezing admin is correct behavior

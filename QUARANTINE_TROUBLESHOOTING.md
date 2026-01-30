# Quarantine Functionality Troubleshooting Guide

## Issue: Sessions Not Being Killed / User Not Frozen

If users are not being properly quarantined (sessions not deleted or account not deactivated), follow these steps:

## Improvements Made

### 1. Enhanced Error Handling
- Added try-catch blocks around session decoding
- Continues processing even if some sessions fail to decode
- Returns detailed error information

### 2. Better Session Matching
- Improved user ID comparison (handles both string and integer IDs)
- More robust session decoding error handling

### 3. Detailed Response Data
- Returns count of deleted sessions
- Shows account status before/after
- Reports any decoding errors

## Testing the Quarantine Function

### Method 1: Using the Test Script

```bash
python test_quarantine.py <user_id>
```

Example:
```bash
python test_quarantine.py 1
```

This will:
- Show current user status
- List all active sessions for the user
- Perform quarantine
- Verify sessions were deleted
- Show detailed results

### Method 2: Using the Management Command

```bash
python manage.py quarantine_user <user_id>
```

Example:
```bash
python manage.py quarantine_user 1
```

### Method 3: Using the API Endpoint

```bash
curl -X POST http://localhost:8000/api/quarantine-user/ \
  -H "Content-Type: application/json" \
  -d '{"user_id": 1}'
```

Expected response:
```json
{
  "status": "success",
  "message": "User ID 1 (username) has been quarantined successfully",
  "user_id": 1,
  "username": "username",
  "account_was_active": true,
  "account_now_active": false,
  "sessions_deleted": 2,
  "expired_sessions_cleaned": 5
}
```

## Common Issues and Solutions

### Issue 1: Sessions Not Found

**Symptoms**: `sessions_deleted: 0` even though user is logged in

**Possible Causes**:
1. Sessions might be stored in a different backend (Redis, database, etc.)
2. Session expiry date might be incorrect
3. User ID mismatch in session data

**Solutions**:
- Check Django `SESSION_ENGINE` in `settings.py`
- Verify session backend: `python manage.py shell` → `from django.conf import settings; print(settings.SESSION_ENGINE)`
- Check if sessions exist: `python manage.py shell` → `from django.contrib.sessions.models import Session; print(Session.objects.count())`

### Issue 2: Account Not Deactivating

**Symptoms**: `account_now_active: true` after quarantine

**Possible Causes**:
1. Database transaction not committed
2. Cached user object
3. Permission issues

**Solutions**:
- Verify in database: `python manage.py shell` → `from django.contrib.auth.models import User; u = User.objects.get(pk=1); print(u.is_active)`
- Check for database transaction issues
- Ensure proper save() call

### Issue 3: Session Decoding Errors

**Symptoms**: `decode_errors_count > 0` in response

**Possible Causes**:
1. Corrupted session data
2. Different session serialization format
3. Session encryption issues

**Solutions**:
- Check `SESSION_SERIALIZER` in settings.py
- Clear corrupted sessions manually
- Verify session backend compatibility

## Debugging Steps

### Step 1: Check Current Sessions

```python
python manage.py shell
```

```python
from django.contrib.sessions.models import Session
from django.utils import timezone
from django.contrib.auth.models import User

# Get all active sessions
sessions = Session.objects.filter(expire_date__gte=timezone.now())
print(f"Total active sessions: {sessions.count()}")

# Check sessions for a specific user
user = User.objects.get(pk=1)
for session in sessions:
    try:
        data = session.get_decoded()
        user_id = data.get('_auth_user_id')
        if user_id and str(user.pk) == str(user_id):
            print(f"Session: {session.session_key}, Expires: {session.expire_date}")
    except Exception as e:
        print(f"Error decoding session {session.session_key}: {e}")
```

### Step 2: Verify User Status

```python
from django.contrib.auth.models import User

user = User.objects.get(pk=1)
print(f"User: {user.username}")
print(f"Active: {user.is_active}")
print(f"ID: {user.pk}")
```

### Step 3: Manual Quarantine Test

```python
from django.contrib.auth.models import User
from django.contrib.sessions.models import Session
from django.utils import timezone

user = User.objects.get(pk=1)

# Deactivate
user.is_active = False
user.save()
print(f"Account deactivated: {user.is_active}")

# Delete sessions
sessions = Session.objects.filter(expire_date__gte=timezone.now())
deleted = 0
for session in sessions:
    try:
        data = session.get_decoded()
        if str(user.pk) == str(data.get('_auth_user_id', '')):
            session.delete()
            deleted += 1
    except:
        pass

print(f"Deleted {deleted} sessions")
```

## Verification Checklist

After running quarantine, verify:

- [ ] User account is inactive (`user.is_active == False`)
- [ ] No active sessions exist for the user
- [ ] User cannot log in (test login attempt)
- [ ] API returns success with session count > 0 (if user had sessions)

## Session Backend Configuration

Check your `settings.py` for session configuration:

```python
# Default: database sessions
SESSION_ENGINE = 'django.contrib.sessions.backends.db'

# Or cached sessions
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'

# Or file-based
SESSION_ENGINE = 'django.contrib.sessions.backends.file'
```

**Note**: The current implementation works with database sessions. If using cache or file-based sessions, you may need to adjust the deletion logic.

## API Response Fields

The quarantine API returns:

- `status`: "success" or "error"
- `user_id`: The user ID that was quarantined
- `username`: The username
- `account_was_active`: Boolean - account status before
- `account_now_active`: Boolean - should be False
- `sessions_deleted`: Number of sessions deleted
- `expired_sessions_cleaned`: Number of expired sessions cleaned up
- `warnings`: Any warnings (e.g., decode errors)
- `decode_errors_count`: Number of sessions that had decoding issues

## Next Steps if Still Not Working

1. Check Django logs for errors
2. Verify database permissions
3. Test with a fresh user session
4. Check if middleware is interfering
5. Verify session backend type
6. Check for custom authentication backends

## Contact

If issues persist, check:
- Django version compatibility
- Session middleware configuration
- Database connection and permissions
- Any custom authentication or session handling code

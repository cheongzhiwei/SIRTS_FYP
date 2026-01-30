"""
Test script for quarantine functionality.
Run this to test if user quarantine is working correctly.

Usage:
    python test_quarantine.py <user_id>

Example:
    python test_quarantine.py 1
"""

import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SIRTS.settings')
django.setup()

from django.contrib.auth.models import User
from django.contrib.sessions.models import Session
from django.utils import timezone
import json

def test_quarantine(user_id):
    """Test the quarantine functionality"""
    print(f"\n{'='*60}")
    print(f"Testing Quarantine for User ID: {user_id}")
    print(f"{'='*60}\n")
    
    try:
        user = User.objects.get(pk=user_id)
        print(f"✓ Found user: {user.username} (ID: {user.id})")
        print(f"  Current status: {'ACTIVE' if user.is_active else 'INACTIVE'}")
        
        # Count active sessions before
        all_sessions = Session.objects.filter(expire_date__gte=timezone.now())
        user_sessions_before = 0
        
        print(f"\nScanning {all_sessions.count()} active sessions...")
        for session in all_sessions:
            try:
                session_data = session.get_decoded()
                session_user_id = session_data.get('_auth_user_id')
                if session_user_id and str(user.pk) == str(session_user_id):
                    user_sessions_before += 1
                    print(f"  - Found session: {session.session_key[:20]}... (expires: {session.expire_date})")
            except Exception as e:
                pass
        
        print(f"\nFound {user_sessions_before} active session(s) for this user")
        
        # Test the quarantine API logic
        print(f"\n{'='*60}")
        print("Testing Quarantine Process...")
        print(f"{'='*60}\n")
        
        # 1. Deactivate account
        was_active = user.is_active
        user.is_active = False
        user.save()
        print(f"✓ Account deactivated: {user.is_active}")
        
        # 2. Delete sessions
        sessions_deleted = 0
        decode_errors = 0
        
        for session in all_sessions:
            try:
                session_data = session.get_decoded()
                session_user_id = session_data.get('_auth_user_id')
                
                if session_user_id and str(user.pk) == str(session_user_id):
                    session_key = session.session_key
                    session.delete()
                    sessions_deleted += 1
                    print(f"✓ Deleted session: {session_key[:20]}...")
            except Exception as e:
                decode_errors += 1
                print(f"✗ Error decoding session: {str(e)}")
        
        # 3. Verify
        print(f"\n{'='*60}")
        print("Verification Results:")
        print(f"{'='*60}\n")
        
        # Check sessions again
        all_sessions_after = Session.objects.filter(expire_date__gte=timezone.now())
        user_sessions_after = 0
        
        for session in all_sessions_after:
            try:
                session_data = session.get_decoded()
                session_user_id = session_data.get('_auth_user_id')
                if session_user_id and str(user.pk) == str(session_user_id):
                    user_sessions_after += 1
            except Exception:
                pass
        
        print(f"Account Status:")
        print(f"  Before: {'ACTIVE' if was_active else 'INACTIVE'}")
        print(f"  After:  {'ACTIVE' if user.is_active else 'INACTIVE'}")
        print(f"\nSessions:")
        print(f"  Before: {user_sessions_before} active session(s)")
        print(f"  Deleted: {sessions_deleted} session(s)")
        print(f"  After: {user_sessions_after} active session(s)")
        print(f"  Decode errors: {decode_errors}")
        
        if user.is_active == False and user_sessions_after == 0:
            print(f"\n{'='*60}")
            print("✓ SUCCESS: User quarantined successfully!")
            print(f"{'='*60}\n")
        else:
            print(f"\n{'='*60}")
            print("⚠ WARNING: Quarantine may not be complete")
            if user.is_active:
                print("  - Account is still active")
            if user_sessions_after > 0:
                print(f"  - {user_sessions_after} session(s) still exist")
            print(f"{'='*60}\n")
        
        # Restore account for testing (optional)
        restore = input("Restore account to active? (y/n): ").lower().strip()
        if restore == 'y':
            user.is_active = True
            user.save()
            print("✓ Account restored to active")
        
    except User.DoesNotExist:
        print(f"✗ ERROR: User ID {user_id} does not exist")
        sys.exit(1)
    except Exception as e:
        print(f"✗ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python test_quarantine.py <user_id>")
        print("\nExample: python test_quarantine.py 1")
        sys.exit(1)
    
    try:
        user_id = int(sys.argv[1])
        test_quarantine(user_id)
    except ValueError:
        print(f"✗ ERROR: Invalid user_id: {sys.argv[1]}")
        sys.exit(1)

"""
Quick script to unfreeze a user account.
Usage: python unfreeze_user.py <user_id>
"""

import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SIRTS.settings')
django.setup()

from django.contrib.auth.models import User

def unfreeze_user(user_id):
    """Unfreeze a user account"""
    try:
        user = User.objects.get(pk=user_id)
        user.is_active = True
        user.save()
        print(f"✓ Successfully unfroze User ID {user_id} ({user.username})")
        return True
    except User.DoesNotExist:
        print(f"✗ User ID {user_id} does not exist")
        return False
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return False

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python unfreeze_user.py <user_id>")
        print("\nExample: python unfreeze_user.py 2")
        sys.exit(1)
    
    try:
        user_id = int(sys.argv[1])
        success = unfreeze_user(user_id)
        sys.exit(0 if success else 1)
    except ValueError:
        print(f"✗ Invalid user_id: {sys.argv[1]}")
        sys.exit(1)

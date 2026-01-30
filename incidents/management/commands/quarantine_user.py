from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.contrib.sessions.models import Session
from django.utils import timezone

class Command(BaseCommand):
    help = 'Freezes a user account and clears all active sessions'

    def add_arguments(self, parser):
        parser.add_argument('user_id', type=int, help='The ID of the user to quarantine')

    def handle(self, *args, **kwargs):
        user_id = kwargs['user_id']
        try:
            user = User.objects.get(pk=user_id)
            
            # 1. Freeze the account
            was_active = user.is_active
            user.is_active = False
            user.save()
            
            if was_active:
                self.stdout.write(f'Account deactivated: User ID {user_id} ({user.username})')
            else:
                self.stdout.write(f'Account was already inactive: User ID {user_id} ({user.username})')

            # 2. Clear all active sessions for this user
            all_sessions = Session.objects.filter(expire_date__gte=timezone.now())
            sessions_deleted = 0
            decode_errors = 0
            
            for session in all_sessions:
                try:
                    session_data = session.get_decoded()
                    session_user_id = session_data.get('_auth_user_id')
                    
                    # Check if this session belongs to the user
                    if session_user_id and str(user.pk) == str(session_user_id):
                        session.delete()
                        sessions_deleted += 1
                except Exception as e:
                    decode_errors += 1
                    continue
            
            # 3. Clean up expired sessions
            expired_deleted = Session.objects.filter(expire_date__lt=timezone.now()).delete()[0]

            self.stdout.write(self.style.SUCCESS(
                f'Successfully quarantined User ID {user_id} ({user.username})\n'
                f'  - Sessions deleted: {sessions_deleted}\n'
                f'  - Expired sessions cleaned: {expired_deleted}'
            ))
            
            if decode_errors > 0:
                self.stdout.write(self.style.WARNING(
                    f'  - Warning: {decode_errors} sessions had decoding issues'
                ))
        
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'User ID {user_id} does not exist'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error quarantining user: {str(e)}'))
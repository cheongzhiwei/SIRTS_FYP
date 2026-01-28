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
            user.is_active = False
            user.save()

            # 2. Clear all active sessions for this user
            all_sessions = Session.objects.filter(expire_date__gte=timezone.now())
            for session in all_sessions:
                if str(user.pk) == session.get_decoded().get('_auth_user_id'):
                    session.delete()

            self.stdout.write(self.style.SUCCESS(f'Successfully quarantined User ID {user_id}'))
        
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'User ID {user_id} does not exist'))
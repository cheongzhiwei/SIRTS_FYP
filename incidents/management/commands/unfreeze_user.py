from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = 'Unfreezes a user account (sets is_active to True)'

    def add_arguments(self, parser):
        parser.add_argument('user_id', type=int, help='The ID of the user to unfreeze')

    def handle(self, *args, **kwargs):
        user_id = kwargs['user_id']
        try:
            user = User.objects.get(pk=user_id)
            
            was_inactive = not user.is_active
            user.is_active = True
            user.save()
            
            if was_inactive:
                self.stdout.write(self.style.SUCCESS(
                    f'Successfully unfroze User ID {user_id} ({user.username})'
                ))
            else:
                self.stdout.write(
                    f'User ID {user_id} ({user.username}) was already active'
                )
        
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'User ID {user_id} does not exist'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error unfreezing user: {str(e)}'))

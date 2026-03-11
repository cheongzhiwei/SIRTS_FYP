from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group


class Command(BaseCommand):
    help = 'Creates the Manager group and optionally adds users to it'

    def add_arguments(self, parser):
        parser.add_argument(
            '--add-users',
            nargs='+',
            type=str,
            help='Usernames to add to the Manager group (space-separated)',
        )
        parser.add_argument(
            '--list-users',
            action='store_true',
            help='List all users currently in the Manager group',
        )

    def handle(self, *args, **kwargs):
        # Create or get the Manager group
        manager_group, created = Group.objects.get_or_create(name='Manager')
        
        if created:
            self.stdout.write(self.style.SUCCESS(
                f'✓ Successfully created "Manager" group'
            ))
        else:
            self.stdout.write(self.style.WARNING(
                f'⚠ "Manager" group already exists'
            ))
        
        # Add users to the group if specified
        usernames_to_add = kwargs.get('add_users', [])
        if usernames_to_add:
            added_count = 0
            not_found = []
            
            for username in usernames_to_add:
                try:
                    user = User.objects.get(username=username)
                    if manager_group not in user.groups.all():
                        manager_group.user_set.add(user)
                        added_count += 1
                        self.stdout.write(self.style.SUCCESS(
                            f'  ✓ Added "{username}" to Manager group'
                        ))
                    else:
                        self.stdout.write(self.style.WARNING(
                            f'  ⚠ "{username}" is already in Manager group'
                        ))
                except User.DoesNotExist:
                    not_found.append(username)
                    self.stdout.write(self.style.ERROR(
                        f'  ✗ User "{username}" not found'
                    ))
            
            if added_count > 0:
                self.stdout.write(self.style.SUCCESS(
                    f'\n✓ Added {added_count} user(s) to Manager group'
                ))
            
            if not_found:
                self.stdout.write(self.style.ERROR(
                    f'\n✗ Could not find {len(not_found)} user(s): {", ".join(not_found)}'
                ))
        
        # List users in the group if requested
        if kwargs.get('list_users'):
            managers = manager_group.user_set.all()
            if managers.exists():
                self.stdout.write(self.style.SUCCESS(
                    f'\nUsers in Manager group ({managers.count()}):'
                ))
                for user in managers.order_by('username'):
                    self.stdout.write(f'  - {user.username} (ID: {user.id})')
            else:
                self.stdout.write(self.style.WARNING(
                    '\nNo users currently in Manager group'
                ))
        
        # If no actions specified, show summary
        if not usernames_to_add and not kwargs.get('list_users'):
            managers_count = manager_group.user_set.count()
            self.stdout.write(self.style.SUCCESS(
                f'\nManager group is ready!'
            ))
            self.stdout.write(f'  Current members: {managers_count}')
            self.stdout.write(f'\nTo add users, run:')
            self.stdout.write(f'  python manage.py create_manager_group --add-users username1 username2')
            self.stdout.write(f'\nTo list current members, run:')
            self.stdout.write(f'  python manage.py create_manager_group --list-users')

from django.core.management.base import BaseCommand
from admin_panel.models import AdminUser


class Command(BaseCommand):
    help = 'Create default admin user for admin panel'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            default='superuser',
            help='Username for admin user (default: superuser)'
        )
        parser.add_argument(
            '--password',
            type=str,
            default='superuser',
            help='Password for admin user (default: superuser)'
        )
        parser.add_argument(
            '--email',
            type=str,
            default='admin@mamicoach.com',
            help='Email for admin user (default: admin@mamicoach.com)'
        )

    def handle(self, *args, **options):
        username = options['username']
        password = options['password']
        email = options['email']
        
        # Check if admin user already exists
        if AdminUser.objects.filter(username=username).exists():
            self.stdout.write(self.style.WARNING(f'Admin user "{username}" already exists!'))
            return
        
        # Create admin user
        admin = AdminUser(username=username, email=email)
        admin.set_password(password)
        admin.save()
        
        self.stdout.write(self.style.SUCCESS(f'Successfully created admin user "{username}"'))
        self.stdout.write(f'Username: {username}')
        self.stdout.write(f'Password: {password}')
        self.stdout.write(f'Email: {email}')

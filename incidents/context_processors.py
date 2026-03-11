from .models import Incident
from django.contrib.auth.models import Group

def incident_monitor(request):
    """
    Counts ONLY 'Open' tickets that belong to the logged-in user.
    Also provides manager check for template access.
    """
    context = {'pending_count': 0, 'is_manager': False}
    
    if request.user.is_authenticated:
        # 1. Filter by User (request.user)
        # 2. Filter by Status ('Open')
        count = Incident.objects.filter(user=request.user, status='Open').count()
        context['pending_count'] = count
        
        # Check if user is a manager (in Manager group)
        try:
            manager_group = Group.objects.get(name='Manager')
            context['is_manager'] = manager_group in request.user.groups.all()
        except Group.DoesNotExist:
            context['is_manager'] = False
    
    return context
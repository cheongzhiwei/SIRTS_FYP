from .models import Incident, Comment, CommentRead
from django.contrib.auth.models import Group

def incident_monitor(request):
    """
    Counts ONLY 'Open' tickets that belong to the logged-in user.
    Also provides manager check for template access.
    """
    context = {'pending_count': 0, 'mail_count': 0, 'is_manager': False}
    
    if request.user.is_authenticated:
        # 1. Filter by User (request.user)
        # 2. Filter by Status ('Open')
        count = Incident.objects.filter(user=request.user, status='Open').count()
        context['pending_count'] = count

        # Unread "mail" count: comments from other users on user's own incidents
        user_incidents = Incident.objects.filter(user=request.user)
        unread_total = 0
        for incident in user_incidents:
            try:
                read_state = CommentRead.objects.get(user=request.user, incident=incident)
                unread_total += Comment.objects.filter(
                    incident=incident,
                    created_at__gt=read_state.last_read_at
                ).exclude(user=request.user).count()
            except CommentRead.DoesNotExist:
                unread_total += Comment.objects.filter(
                    incident=incident
                ).exclude(user=request.user).count()
        context['mail_count'] = unread_total
        
        # Check if user is a manager (in Manager group)
        try:
            manager_group = Group.objects.get(name='Manager')
            context['is_manager'] = manager_group in request.user.groups.all()
        except Group.DoesNotExist:
            context['is_manager'] = False
    
    return context
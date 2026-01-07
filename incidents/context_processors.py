from .models import Incident

def incident_monitor(request):
    """
    Counts ONLY 'Open' tickets that belong to the logged-in user.
    """
    if request.user.is_authenticated:
        # 1. Filter by User (request.user)
        # 2. Filter by Status ('Open')
        count = Incident.objects.filter(user=request.user, status='Open').count()
        return {'pending_count': count}
    
    return {'pending_count': 0}
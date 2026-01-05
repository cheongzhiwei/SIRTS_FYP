from .models import Incident

def ticket_counts(request):
    if request.user.is_authenticated:
        # Count all tickets that are NOT 'Closed'
        pending_count = Incident.objects.filter(status='Open').count()
        return {'pending_count': pending_count}
    return {}
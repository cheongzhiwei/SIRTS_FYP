from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q
from .models import Incident
from django.shortcuts import get_object_or_404

# --- 1. REPORT INCIDENT (With Smart Logic) ---
@login_required
def report_incident(request):
    if request.method == 'POST':
        title_data = request.POST.get('title')
        description_data = request.POST.get('description')
        action_type = request.POST.get('action_type')  # <--- Check which button was clicked

        # Determine Status
        # If they clicked "Issue Solved", we mark it 'Self-Fixed'
        if action_type == 'solved':
            incident_status = 'Self-Fixed' 
            message_text = "Great! We recorded that this issue was resolved automatically."
        else:
            incident_status = 'Open'
            message_text = "Incident reported successfully!"

        # Save to Database
        Incident.objects.create(
            reporter=request.user,
            title=title_data,
            description=description_data,
            status=incident_status
        )
        
        messages.success(request, message_text)
        return redirect('report_incident')

    # Point to the new HTML file we made
    return render(request, 'final_report.html')

# --- 2. USER HISTORY (The Missing Part) ---
@login_required
def user_history(request):
    # Fetch tickets created by THIS user
    my_tickets = Incident.objects.filter(reporter=request.user).order_by('-created_at')
    return render(request, 'user_history.html', {'tickets': my_tickets})

# 📊 NEW ADMIN DASHBOARD VIEW
@login_required
def admin_dashboard(request):
    if not request.user.is_superuser:
        return render(request, '403_forbidden.html')

    # 1. SETUP DATES (Default to Current Week)
    today = timezone.now().date()
    # Find start of week (Monday)
    start_of_week = today - timedelta(days=today.weekday())
    
    # Get Date Filters from Search Form (or use default)
    date_from = request.GET.get('date_from', start_of_week.strftime('%Y-%m-%d'))
    date_to = request.GET.get('date_to', today.strftime('%Y-%m-%d'))
    status_filter = request.GET.get('status', '')
    issue_search = request.GET.get('issue', '')

    # 2. BASE QUERY (Filter by Date Range)
    # We filter ONLY by date first, because the "Boxes" need to respect the date range
    tickets = Incident.objects.filter(created_at__date__gte=date_from, created_at__date__lte=date_to)

    # 3. APPLY EXTRA FILTERS (Status & Issue Name)
    if status_filter:
        tickets = tickets.filter(status=status_filter)
    
    if issue_search:
        tickets = tickets.filter(Q(title__icontains=issue_search) | Q(description__icontains=issue_search))

    # 4. CALCULATE BOX STATS (Based on the Date Range)
    # Box 1: Open
    count_open = tickets.filter(status='Open').count()
    # Box 2: Self Fixed
    count_fixed = tickets.filter(status='Self-Fixed').count()
    # Box 3: Closed (We assume 'Closed' is a status we might add later, currently showing 0 or existing)
    count_closed = tickets.filter(status='Closed').count() 
    
# ... inside admin_dashboard function ...

    # 4. CALCULATE BOX STATS
    count_open = tickets.filter(status='Open').count()
    count_fixed = tickets.filter(status='Self-Fixed').count()
    count_closed = tickets.filter(status='Closed').count()
    
    # NEW: Total Tickets (Filtered)
    count_total = tickets.count()  # <--- ADD THIS LINE

    # Box 4: Total Open THIS YEAR (Special KPI)
    start_of_year = today.replace(month=1, day=1)
    count_year_open = Incident.objects.filter(created_at__date__gte=start_of_year, status='Open').count()

    context = {
        'tickets': tickets.order_by('-created_at'),
        'count_open': count_open,
        'count_fixed': count_fixed,
        'count_closed': count_closed,
        'count_total': count_total,      # <--- ADD THIS to context
        'count_year_open': count_year_open,
        'date_from': date_from,
        'date_to': date_to,
        'status_filter': status_filter,
        'issue_search': issue_search
    }
    return render(request, 'admin_dashboard.html', context)

@login_required
def manage_ticket(request, ticket_id):
    if not request.user.is_superuser:
        return render(request, '403_forbidden.html')

    # 1. Get the specific ticket
    ticket = get_object_or_404(Incident, id=ticket_id)

    if request.method == 'POST':
        # 2. Update Status
        new_status = request.POST.get('status')
        admin_note = request.POST.get('admin_notes')
        
        ticket.status = new_status
        # We will add a field for notes later, for now just save status
        ticket.save()
        
        return redirect('admin_dashboard')

    return render(request, 'manage_ticket.html', {'ticket': ticket})
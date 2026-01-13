from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from .models import Incident
from datetime import datetime, timedelta, date
from django.utils import timezone
from django.http import JsonResponse

@login_required
def home(request):
    # Shows the user's own incident history with status overview
    incidents = Incident.objects.filter(user=request.user).order_by('-created_at')
    
    # Get filter parameters
    status_filter = request.GET.get('status')
    period_filter = request.GET.get('period', 'week')  # Default to week
    from_date = request.GET.get('from')
    to_date = request.GET.get('to')
    
    # Period filtering (today, week, month, all)
    today = timezone.now().date()
    
    # Helper function to get period filter queryset
    def get_period_queryset(base_queryset):
        # If date range is specified, use it instead of period
        if from_date or to_date:
            queryset = base_queryset
            if from_date:
                try:
                    from_date_obj = datetime.strptime(from_date, '%d/%m/%Y').date()
                except ValueError:
                    try:
                        from_date_obj = datetime.strptime(from_date, '%Y-%m-%d').date()
                    except ValueError:
                        from_date_obj = None
                if from_date_obj:
                    queryset = queryset.filter(created_at__date__gte=from_date_obj)
            if to_date:
                try:
                    to_date_obj = datetime.strptime(to_date, '%d/%m/%Y').date()
                except ValueError:
                    try:
                        to_date_obj = datetime.strptime(to_date, '%Y-%m-%d').date()
                    except ValueError:
                        to_date_obj = None
                if to_date_obj:
                    queryset = queryset.filter(created_at__date__lte=to_date_obj)
            return queryset
        
        # Otherwise use period filter
        if period_filter == 'today':
            return base_queryset.filter(created_at__date=today)
        elif period_filter == 'week':
            week_start = today - timedelta(days=today.weekday())
            return base_queryset.filter(created_at__date__gte=week_start)
        elif period_filter == 'month':
            return base_queryset.filter(created_at__year=today.year, created_at__month=today.month)
        else:  # 'all'
            return base_queryset
    
    # Apply period/date range filtering
    incidents = get_period_queryset(incidents)
    
    # Status filtering
    if status_filter:
        incidents = incidents.filter(status=status_filter)
    
    # Process incidents to extract smart scanner suggestions
    processed_incidents = []
    for incident in incidents:
        incident_dict = {
            'incident': incident,
            'smart_suggestions': []
        }
        
        # Extract smart scanner suggestions if status is Resolved
        if incident.status == 'Resolved' and incident.description:
            # New format: description IS the suggestions (no prefix)
            if 'Smart Scanner Suggestions:' in incident.description:
                # Old format: Extract suggestions after "Smart Scanner Suggestions:"
                suggestions_text = incident.description.split('Smart Scanner Suggestions:')[1].strip()
                incident_dict['smart_suggestions'] = [s.strip() for s in suggestions_text.split('\n') if s.strip()]
            elif 'Reported via Smart Scanner' not in incident.description and 'Issue resolved via Smart Scanner quick fixes.' not in incident.description:
                # New format: Description is directly the suggestions, split by newline
                incident_dict['smart_suggestions'] = [s.strip() for s in incident.description.split('\n') if s.strip()]
        
        processed_incidents.append(incident_dict)
    
    # Calculate status counts based on filtered data (for status bar)
    status_bar_base = Incident.objects.filter(user=request.user)
    status_bar_base = get_period_queryset(status_bar_base)
    
    status_counts = {
        'open': status_bar_base.filter(status='Open').count(),
        'resolved': status_bar_base.filter(status='Resolved').count(),
        'closed': status_bar_base.filter(status='Closed').count(),
        'total': status_bar_base.count()
    }
    
    # Format dates for display in template (dd/mm/yyyy)
    from_date_display = None
    to_date_display = None
    if from_date:
        try:
            from_date_obj = datetime.strptime(from_date, '%d/%m/%Y').date()
            from_date_display = from_date_obj.strftime('%d/%m/%Y')
        except ValueError:
            try:
                from_date_obj = datetime.strptime(from_date, '%Y-%m-%d').date()
                from_date_display = from_date_obj.strftime('%d/%m/%Y')
            except ValueError:
                from_date_display = from_date
    
    if to_date:
        try:
            to_date_obj = datetime.strptime(to_date, '%d/%m/%Y').date()
            to_date_display = to_date_obj.strftime('%d/%m/%Y')
        except ValueError:
            try:
                to_date_obj = datetime.strptime(to_date, '%Y-%m-%d').date()
                to_date_display = to_date_obj.strftime('%d/%m/%Y')
            except ValueError:
                to_date_display = to_date
    
    context = {
        'incidents': incidents,
        'processed_incidents': processed_incidents,
        'tickets': incidents,
        'status_counts': status_counts,
        'period_filter': period_filter,
        'from_date_display': from_date_display,
        'to_date_display': to_date_display,
    }
    return render(request, 'home.html', context)

@login_required
def report_incident(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        status_value = request.POST.get('status', 'Open')
        smart_suggestions = request.POST.get('smart_suggestions', '')
        
        # Validate title word count (max 10 words)
        if title:
            title_words = title.strip().split()
            if len(title_words) > 10:
                messages.error(request, "Issue title cannot exceed 10 words. Please shorten your title.")
                return render(request, 'report_incident.html')
        
        # Get description from form
        description = request.POST.get('description', '').strip()
        
        # If status is Resolved and we have smart suggestions, save them as description
        if status_value == 'Resolved' and smart_suggestions:
            # Save the actual suggestions as the description (e.g., "Unplug and plug it back in.\nRestart your laptop.")
            if description:
                description = description + "\n\nSmart Scanner Solutions:\n" + smart_suggestions.strip()
            else:
                description = smart_suggestions.strip()
        elif status_value == 'Resolved' and not description:
            description = "Issue resolved via Smart Scanner quick fixes."
        elif not description:
            description = "Reported via Smart Scanner"

        # Create incident
        incident = Incident.objects.create(
            user=request.user,
            title=title,
            description=description,
            status=status_value
        )
        
        # If self-fixed, set resolved_at to created_at (same date)
        if status_value == 'Resolved':
            incident.resolved_at = incident.created_at
            incident.save()
        
        if status_value == 'Resolved':
            messages.success(request, "🎉 Great! Your issue is recorded as Self-Fixed.")
        else:
            messages.success(request, "Ticket submitted successfully. IT will review it.")
            
        return redirect('home')

    return render(request, 'report_incident.html')

@login_required
def admin_dashboard(request):
    if not request.user.is_staff:
        return redirect('home')

    # Basic Filtering Logic
    incidents = Incident.objects.all().order_by('-created_at')
    
    status_filter = request.GET.get('status')
    user_filter = request.GET.get('user')
    model_filter = request.GET.get('model')
    period_filter = request.GET.get('period', 'all')
    from_date = request.GET.get('from')
    to_date = request.GET.get('to')
    dept_filter = request.GET.get('dept')

    # Period filtering (today, week, month, all)
    today = timezone.now().date()
    
    # Helper function to get period filter queryset
    def get_period_queryset(base_queryset):
        # If date range is specified, use it instead of period
        if from_date or to_date:
            queryset = base_queryset
            if from_date:
                # Convert string to date object if needed
                if isinstance(from_date, str):
                    # Try dd/mm/yyyy format first, then yyyy-mm-dd
                    try:
                        from_date_obj = datetime.strptime(from_date, '%d/%m/%Y').date()
                    except ValueError:
                        try:
                            from_date_obj = datetime.strptime(from_date, '%Y-%m-%d').date()
                        except ValueError:
                            from_date_obj = None
                else:
                    from_date_obj = from_date
                if from_date_obj:
                    queryset = queryset.filter(created_at__date__gte=from_date_obj)
            if to_date:
                # Convert string to date object if needed
                if isinstance(to_date, str):
                    # Try dd/mm/yyyy format first, then yyyy-mm-dd
                    try:
                        to_date_obj = datetime.strptime(to_date, '%d/%m/%Y').date()
                    except ValueError:
                        try:
                            to_date_obj = datetime.strptime(to_date, '%Y-%m-%d').date()
                        except ValueError:
                            to_date_obj = None
                else:
                    to_date_obj = to_date
                if to_date_obj:
                    queryset = queryset.filter(created_at__date__lte=to_date_obj)
            return queryset
        
        # Otherwise use period filter
        if period_filter == 'today':
            return base_queryset.filter(created_at__date=today)
        elif period_filter == 'week':
            week_start = today - timedelta(days=today.weekday())
            return base_queryset.filter(created_at__date__gte=week_start)
        elif period_filter == 'month':
            return base_queryset.filter(created_at__year=today.year, created_at__month=today.month)
        else:  # 'all'
            return base_queryset
    
    # Apply period/date range filtering to incidents
    incidents = get_period_queryset(incidents)

    # Status filtering
    if status_filter:
        incidents = incidents.filter(status=status_filter)
    
    # User filtering
    if user_filter:
        incidents = incidents.filter(user__username__icontains=user_filter)
    
    # Department filtering
    if dept_filter:
        incidents = incidents.filter(user__employeeprofile__department=dept_filter)
    
    # Model filtering (if laptop model exists)
    if model_filter:
        incidents = incidents.filter(user__employeeprofile__laptop_model__icontains=model_filter)

    # Summary Counts - apply ALL filters (except status) to status bar counts
    # This ensures status bars reflect the current filter context
    status_bar_base = Incident.objects.all()
    
    # Apply period/date range filter
    status_bar_base = get_period_queryset(status_bar_base)
    
    # Apply department filter (if set)
    if dept_filter:
        status_bar_base = status_bar_base.filter(user__employeeprofile__department=dept_filter)
    
    # Apply laptop model filter (if set)
    if model_filter:
        status_bar_base = status_bar_base.filter(user__employeeprofile__laptop_model__icontains=model_filter)
    
    # Apply user filter (if set) - this might be useful for status bars too
    if user_filter:
        status_bar_base = status_bar_base.filter(user__username__icontains=user_filter)
    
    # Note: We don't apply status filter to status_bar_base because we want to count all statuses
    # The status filter only affects the ticket list, not the status bar counts
    
    # Format dates for display in template (dd/mm/yyyy)
    from_date_display = None
    to_date_display = None
    if from_date:
        try:
            # Try parsing dd/mm/yyyy first
            from_date_obj = datetime.strptime(from_date, '%d/%m/%Y').date()
            from_date_display = from_date_obj.strftime('%d/%m/%Y')
        except ValueError:
            try:
                # Try parsing yyyy-mm-dd
                from_date_obj = datetime.strptime(from_date, '%Y-%m-%d').date()
                from_date_display = from_date_obj.strftime('%d/%m/%Y')
            except ValueError:
                from_date_display = from_date
    
    if to_date:
        try:
            # Try parsing dd/mm/yyyy first
            to_date_obj = datetime.strptime(to_date, '%d/%m/%Y').date()
            to_date_display = to_date_obj.strftime('%d/%m/%Y')
        except ValueError:
            try:
                # Try parsing yyyy-mm-dd
                to_date_obj = datetime.strptime(to_date, '%Y-%m-%d').date()
                to_date_display = to_date_obj.strftime('%d/%m/%Y')
            except ValueError:
                to_date_display = to_date
    
    context = {
        'incidents': incidents,
        'open_count': status_bar_base.filter(status='Open').count(),
        'resolved_count': status_bar_base.filter(status='Resolved').count(),
        'closed_count': status_bar_base.filter(status='Closed').count(),
        'open_year_count': Incident.objects.filter(status='Open', created_at__year=datetime.now().year).count(),
        'all_count': status_bar_base.count(),
        'period_filter': period_filter,  # Pass period to template
        'from_date_display': from_date_display,  # Formatted date for display
        'to_date_display': to_date_display,  # Formatted date for display
    }
    return render(request, 'admin_dashboard.html', context)
@login_required
def manage_ticket(request, ticket_id):
    if not request.user.is_staff:
        return redirect('home')
        
    ticket = Incident.objects.get(id=ticket_id)
    
    if request.method == 'POST':
        # Check if this is a delete request
        if 'delete_ticket' in request.POST and request.user.is_superuser:
            ticket_id_for_message = ticket.id
            ticket.delete()
            messages.success(request, f"Ticket #{ticket_id_for_message} deleted successfully.")
            return redirect('admin_dashboard')
        
        # Update ticket fields
        new_status = request.POST.get('status')
        admin_response = request.POST.get('admin_notes', '').strip()
        
        # Allow superuser to edit ticket content
        if request.user.is_superuser:
            title = request.POST.get('title', '').strip()
            description = request.POST.get('description', '').strip()
            if title:
                ticket.title = title
            if description:
                ticket.description = description
        
        ticket.status = new_status
        if admin_response:
            ticket.admin_response = admin_response
        # Track which admin resolved the ticket and when
        if new_status == 'Closed':
            if admin_response:
                ticket.resolved_by = request.user
            if not ticket.resolved_at:
                ticket.resolved_at = timezone.now()
        ticket.save()
        messages.success(request, f"Ticket #{ticket.id} updated successfully.")
        return redirect('admin_dashboard')

    return render(request, 'manage_ticket.html', {'ticket': ticket})

def user_login(request):
    if request.method == 'POST':
        u = request.POST.get('username')
        p = request.POST.get('password')
        user = authenticate(request, username=u, password=p)
        if user is not None:
            login(request, user)
            return redirect('home')
        else:
            messages.error(request, "Invalid username or password")
    return render(request, 'login.html')

def user_logout(request):
    logout(request)
    return redirect('login')

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Registration successful!")
            return redirect('home')
    else:
        form = UserCreationForm()
    return render(request, 'register.html', {'form': form})

from django.http import JsonResponse

@login_required
def incident_calendar_data(request):
    """
    Returns JSON data for calendar events.
    Shows incidents with created date and resolved date (if available).
    Like Google Calendar, shows when incidents were created and when they were resolved.
    """
    if not request.user.is_staff:
        return JsonResponse([], safe=False)
    
    # Fetch all incidents for the calendar
    incidents = Incident.objects.all()
    events = []
    
    for incident in incidents:
        # Determine color based on status
        color = '#dc3545'  # Red for Open
        if incident.status == 'Resolved':
            color = '#007bff'  # Blue for Self-Fixed
        elif incident.status == 'Closed':
            color = '#28a745'  # Green for Closed
        
        # Create event for incident creation
        created_event = {
            'id': f"{incident.id}_created",
            'title': f"#{incident.id}: {incident.title}",
            'start': incident.created_at.isoformat(),
            'backgroundColor': color,
            'borderColor': color,
            'url': f"/manage/{incident.id}/",
            'extendedProps': {
                'status': incident.status,
                'reporter': incident.user.username,
                'event_type': 'created'
            }
        }
        
        # If resolved, show as a date range from created to resolved
        if incident.resolved_at:
            created_event['end'] = incident.resolved_at.isoformat()
            created_event['title'] = f"#{incident.id}: {incident.title} (Resolved)"
            # Also add a separate marker for resolution date
            events.append({
                'id': f"{incident.id}_resolved",
                'title': f"#{incident.id}: Resolved",
                'start': incident.resolved_at.isoformat(),
                'backgroundColor': '#28a745',  # Green for resolved
                'borderColor': '#28a745',
                'url': f"/manage/{incident.id}/",
                'extendedProps': {
                    'status': incident.status,
                    'reporter': incident.user.username,
                    'event_type': 'resolved'
                }
            })
        
        events.append(created_event)
    
    return JsonResponse(events, safe=False)

@login_required
def incident_calendar(request):
    """
    Renders the calendar page.
    Shows incidents when created and when resolved (like Google Calendar).
    """
    if not request.user.is_staff:
        return redirect('home')
    return render(request, 'calender.html')
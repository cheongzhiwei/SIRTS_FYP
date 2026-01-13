from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.contrib import messages
from .models import Incident
from datetime import datetime, timedelta, date
from django.utils import timezone
from django.http import JsonResponse
from django.urls import reverse

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
        action_type = request.POST.get('action_type')
        status_value = request.POST.get('status', 'Open')
        smart_suggestions = request.POST.get('smart_suggestions', '')
        
        # Handle action_type from final_report.html form
        if action_type == 'solved':
            status_value = 'Resolved'
        elif action_type == 'submit':
            status_value = 'Open'
        
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

        # 1. Create the incident object but don't save to DB yet
        incident = Incident(
            user=request.user,
            title=title,
            description=description,
            status=status_value
        )
        
        # 2. THE STRENGTHENING STEP: Auto-pull profile data
        # We look up the EmployeeProfile to "lock" the hardware info into the ticket
        profile = getattr(request.user, 'employeeprofile', None)
        if profile:
            incident.laptop_model = profile.laptop_model
            incident.laptop_serial = profile.laptop_serial # Snapshot serial number
            incident.department = profile.get_department_display()
            
        # 3. Save the incident with the "Snapshot" locked in
        incident.save()
        
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
    """
    Dashboard view for managing tickets.
    Only allows updating status and admin notes.
    Edit and delete must be done in Django admin.
    """
    if not request.user.is_staff:
        return redirect('home')
        
    ticket = Incident.objects.get(id=ticket_id)
    
    if request.method == 'POST':
        # Only allow updating status and admin notes
        # Edit and delete are only allowed in Django admin
        new_status = request.POST.get('status')
        admin_response = request.POST.get('admin_notes', '').strip()
        
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
    incidents = Incident.objects.all()
     
    """
    Returns JSON data for calendar events.
    Shows incidents with created date and resolved date (if available).
    Like Google Calendar, shows when incidents were created and when they were resolved.
    Supports filtering by status and resolved_by admin.
    """
    if not request.user.is_staff:
        return JsonResponse([], safe=False)
    
    # Get filter parameters
    status_filter = request.GET.get('status', '')
    admin_filter = request.GET.get('admin', '')
    
    # Fetch all incidents for the calendar
    incidents = Incident.objects.all()
    
    # Apply status filter
    if status_filter:
        incidents = incidents.filter(status=status_filter)
    
    # Apply admin filter (resolved_by)
    if admin_filter:
        incidents = incidents.filter(resolved_by_id=admin_filter)
    
    events = []
    
    for incident in incidents:
        # Determine the primary date and label based on status
        if incident.status == 'Closed' and incident.resolved_at:
            # Show on the date IT fixed it
            event_date = incident.resolved_at
            title = f"CLOSED #{incident.id}"
            color = '#28a745' # Green
        elif incident.status == 'Resolved':
            # Show on the date user fixed it (usually created_at)
            event_date = incident.created_at
            title = f"SELF-FIXED #{incident.id}"
            color = '#007bff' # Blue
        else:
            # Show on the date reported
            event_date = incident.created_at
            title = f"OPEN #{incident.id}"
            color = '#dc3545' # Red

        # Create single-day event (no end date, only start date)
        events.append({
            'title': f"{title}: {incident.title}",
            'start': event_date.date().isoformat(), # Only use the date part (YYYY-MM-DD format)
            'allDay': True, # Single-day event without time
            'backgroundColor': color,
            'borderColor': color,
            'url': reverse('manage_ticket', args=[incident.id]),
        })
        
    return JsonResponse(events, safe=False)

@login_required
def incident_calendar(request):
    """
    Renders the calendar page.
    Shows incidents when created and when resolved (like Google Calendar).
    """
    if not request.user.is_staff:
        return redirect('home')
    
    # Get all staff members from Django admin (is_staff=True)
    # This includes all staff like "admin" and "admin 1"
    all_staff_members = User.objects.filter(
        is_staff=True
    ).distinct().order_by('username')
    
    # Get current filter values
    status_filter = request.GET.get('status', '')
    admin_filter = request.GET.get('admin', '')
    
    context = {
        'staff_members': all_staff_members,
        'status_filter': status_filter,
        'admin_filter': admin_filter,
    }
    
    return render(request, 'calender.html', context)
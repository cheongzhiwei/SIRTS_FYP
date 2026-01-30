from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.sessions.models import Session
from .models import Incident, EmployeeProfile, Comment, CommentRead
from datetime import datetime, timedelta, date
from django.utils import timezone
from django.http import JsonResponse
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
import json
import requests
import hashlib


@login_required
def home(request):

    # Shows the user's own incident history with status overview
    incidents = Incident.objects.filter(user=request.user).prefetch_related('comments').order_by('-created_at')
    
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
    
    # Process incidents to extract smart scanner suggestions and calculate unread comments
    processed_incidents = []
    for incident in incidents:
        incident_dict = {
            'incident': incident,
            'smart_suggestions': [],
            'unread_comments_count': 0
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
        
        # Calculate unread comments count
        # Check if there are any comments
        if incident.comments.exists():
            try:
                comment_read = CommentRead.objects.get(user=request.user, incident=incident)
                # Count comments created after last read
                unread_comments = incident.comments.filter(created_at__gt=comment_read.last_read_at)
                incident_dict['unread_comments_count'] = unread_comments.count()
            except CommentRead.DoesNotExist:
                # User has never read comments, so all comments are unread
                incident_dict['unread_comments_count'] = incident.comments.count()
        
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

        # 1. Handle file upload and generate SHA256 hash for VirusTotal
        file_hash = ""
        attachment_file = None
        
        if 'attachment' in request.FILES:
            file_obj = request.FILES['attachment']
            
            # Generate SHA256 hash for VirusTotal scanning
            # Read file content into memory for hashing (Django will handle saving)
            file_content = b''
            sha256_hash = hashlib.sha256()
            
            # Read file in chunks to handle large files safely
            for chunk in file_obj.chunks():
                sha256_hash.update(chunk)
                file_content += chunk
            
            file_hash = sha256_hash.hexdigest()
            
            # Create a new file-like object from the content for Django to save
            from django.core.files.base import ContentFile
            attachment_file = ContentFile(file_content, name=file_obj.name)
        
        # 2. Create the incident object but don't save to DB yet
        incident = Incident(
            user=request.user,
            title=title,
            description=description,
            status=status_value,
            attachment=attachment_file,
            file_hash=file_hash
        )
        
        # 3. THE STRENGTHENING STEP: Auto-pull profile data
        # We look up the EmployeeProfile to "lock" the hardware info into the ticket
        profile = getattr(request.user, 'employeeprofile', None)
        if profile:
            incident.laptop_model = profile.laptop_model
            incident.laptop_serial = profile.laptop_serial # Snapshot serial number
            incident.department = profile.get_department_display()
            
        # 4. Save the incident with the "Snapshot" locked in
        incident.save()
        
        # If self-fixed, set resolved_at to created_at (same date)
        if status_value == 'Resolved':
            incident.resolved_at = incident.created_at
            incident.save()
        
        if status_value == 'Resolved':
            messages.success(request, "🎉 Great! Your issue is recorded as Self-Fixed.")
        else:
            messages.success(request, "Ticket submitted successfully. IT will review it.")
        
        # 5. Trigger n8n Webhook with file_hash and file_url for VirusTotal scanning
        from django.conf import settings
        n8n_url = f"{settings.EXTERNAL_BASE_URL}/webhook-test/new-incident"
        
        # Build file URL that n8n can access (use EXTERNAL_BASE_URL if available, otherwise use request host)
        file_url = ""
        if incident.attachment:
            try:
                # Use EXTERNAL_BASE_URL from settings so n8n can access the file
                if hasattr(settings, 'EXTERNAL_BASE_URL') and settings.EXTERNAL_BASE_URL:
                    base_url = settings.EXTERNAL_BASE_URL.rstrip('/')
                    attachment_path = incident.attachment.url.lstrip('/')
                    file_url = f"{base_url}/{attachment_path}"
                else:
                    # Fallback to request-based URL
                    file_url = request.build_absolute_uri(incident.attachment.url)
            except Exception as e:
                # Fallback to request-based URL if external URL fails
                print(f"Error building file URL: {e}")
                try:
                    file_url = request.build_absolute_uri(incident.attachment.url)
                except:
                    file_url = ""
        
        payload = {
            "ticket_id": incident.id,
            "title": incident.title,
            "department": incident.department,
            "laptop_serial": incident.laptop_serial,  # Uses your hardware snapshot
            "reported_by": request.user.username,
            "reported_by_id": request.user.id,  # Include user ID for quarantine functionality
            "user_id": request.user.id,  # Alternative field name
            "file_hash": file_hash if file_hash else "",  # Include file hash for VirusTotal
            "file_url": file_url  # File URL for n8n to download and upload to VirusTotal
        }
        
        try:
            requests.post(n8n_url, json=payload, timeout=5)
        except Exception as e:
            print(f"n8n Webhook failed: {e}")
            
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
    serial_filter = request.GET.get('serial')  # Filter by laptop serial number
    view_user = request.GET.get('view_user')  # View all history for a specific user
    view_serial = request.GET.get('view_serial')  # View all history for a specific laptop serial

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
    
    # If viewing specific user or serial history, bypass period filter and show all
    if view_user:
        incidents = incidents.filter(user__username=view_user)
        # Don't apply period filter when viewing user history
    elif view_serial:
        incidents = incidents.filter(laptop_serial=view_serial)
        # Don't apply period filter when viewing serial history
    else:
        # Apply period/date range filtering to incidents
        incidents = get_period_queryset(incidents)

    # Status filtering
    # If filtering by "Open", include both "Open" and "In Progress" statuses
    if status_filter:
        if status_filter == 'Open':
            incidents = incidents.filter(status__in=['Open', 'In Progress'])
        else:
            incidents = incidents.filter(status=status_filter)
    
    # User filtering (only if not viewing specific user)
    if user_filter and not view_user:
        incidents = incidents.filter(user__username__icontains=user_filter)
    
    # Department filtering - filter by user's current department from EmployeeProfile
    if dept_filter:
        incidents = incidents.filter(user__employeeprofile__department=dept_filter)
    
    # Model filtering (if laptop model exists)
    if model_filter:
        incidents = incidents.filter(laptop_model__icontains=model_filter)
    
    # Serial filtering (only if not viewing specific serial)
    if serial_filter and not view_serial:
        incidents = incidents.filter(laptop_serial__icontains=serial_filter)

    # Summary Counts - apply ALL filters (except status) to status bar counts
    # This ensures status bars reflect the current filter context
    status_bar_base = Incident.objects.all()
    
    # If viewing specific user or serial history, show all history (no period filter)
    if view_user:
        status_bar_base = status_bar_base.filter(user__username=view_user)
    elif view_serial:
        status_bar_base = status_bar_base.filter(laptop_serial=view_serial)
    else:
        # Apply period/date range filter
        status_bar_base = get_period_queryset(status_bar_base)
    
    # Apply department filter (if set) - filter by user's current department from EmployeeProfile
    if dept_filter:
        status_bar_base = status_bar_base.filter(user__employeeprofile__department=dept_filter)
    
    # Apply laptop model filter (if set)
    if model_filter:
        status_bar_base = status_bar_base.filter(laptop_model__icontains=model_filter)
    
    # Apply user filter (if set) - this might be useful for status bars too
    if user_filter and not view_user:
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
    
    # Get context info for display
    view_user_display = None
    view_serial_display = None
    if view_user:
        try:
            user_obj = User.objects.get(username=view_user)
            view_user_display = user_obj.username
        except User.DoesNotExist:
            pass
    if view_serial:
        view_serial_display = view_serial
    
    # Calculate status counts - include "In Progress" in "Open" count
    open_count = status_bar_base.filter(status__in=['Open', 'In Progress']).count()
    resolved_count = status_bar_base.filter(status='Resolved').count()
    closed_count = status_bar_base.filter(status='Closed').count()
    open_year_count = Incident.objects.filter(status__in=['Open', 'In Progress'], created_at__year=datetime.now().year).count()
    
    # Calculate unread comments for each incident (for IT staff)
    incidents_with_unread = []
    for incident in incidents:
        unread_count = 0
        if incident.comments.exists():
            try:
                comment_read = CommentRead.objects.get(user=request.user, incident=incident)
                unread_count = incident.comments.filter(created_at__gt=comment_read.last_read_at).count()
            except CommentRead.DoesNotExist:
                unread_count = incident.comments.count()
        incidents_with_unread.append({
            'incident': incident,
            'unread_comments_count': unread_count
        })
    
    context = {
        'incidents': incidents,
        'incidents_with_unread': incidents_with_unread,  # For template to show notifications
        'open_count': open_count,
        'resolved_count': resolved_count,
        'closed_count': closed_count,
        'open_year_count': open_year_count,
        'all_count': status_bar_base.count(),
        'period_filter': period_filter,  # Pass period to template
        'from_date_display': from_date_display,  # Formatted date for display
        'to_date_display': to_date_display,  # Formatted date for display
        'view_user': view_user_display,  # User being viewed
        'view_serial': view_serial_display,  # Serial being viewed
        'department_choices': EmployeeProfile.DEPARTMENT_CHOICES,  # Department choices for dropdown
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
        
    ticket = Incident.objects.prefetch_related('comments').get(id=ticket_id)
    
    # Mark comments as read when viewing the ticket
    CommentRead.objects.update_or_create(
        user=request.user,
        incident=ticket,
        defaults={'last_read_at': timezone.now()}
    )
    
    if request.method == 'POST':
        # Check if this is a status update (not a comment or acknowledgment)
        # Status update form has 'status' field and optionally 'update_status' button, 
        # comment form has 'message' field, acknowledge form goes to different URL
        if ('status' in request.POST or 'update_status' in request.POST) and 'message' not in request.POST:
            # Prevent updates to closed tickets
            if ticket.status == 'Closed':
                messages.error(request, "Cannot update a closed ticket.")
                return render(request, 'manage_ticket.html', {'ticket': ticket})
            
            # Only allow updating status and admin notes
            # Edit and delete are only allowed in Django admin
            new_status = request.POST.get('status', '').strip()
            admin_response = request.POST.get('admin_notes', '').strip()
            
            # Validate status
            valid_statuses = ['Open', 'In Progress', 'Resolved', 'Closed']
            if not new_status or new_status not in valid_statuses:
                messages.error(request, f"Invalid status: {new_status}")
                return render(request, 'manage_ticket.html', {'ticket': ticket})
            
            # Update ticket status
            old_status = ticket.status
            ticket.status = new_status
            
            # Update admin response if provided
            if admin_response:
                ticket.admin_response = admin_response
            
            # Track which admin resolved the ticket and when
            if new_status == 'Closed':
                ticket.resolved_by = request.user
                if not ticket.resolved_at:
                    ticket.resolved_at = timezone.now()
            elif new_status == 'Resolved':
                # If changing to Resolved, set resolved_at if not already set
                if not ticket.resolved_at:
                    ticket.resolved_at = timezone.now()
            
            # Save the ticket
            try:
                ticket.save()
                messages.success(request, f"Ticket #{ticket.id} status updated from '{old_status}' to '{new_status}' successfully.")
                return redirect('admin_dashboard')
            except Exception as e:
                messages.error(request, f"Error updating ticket: {str(e)}")
                return render(request, 'manage_ticket.html', {'ticket': ticket})

    return render(request, 'manage_ticket.html', {'ticket': ticket})

def user_login(request):
    # If user is already logged in, redirect them
    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect('admin_dashboard')
        return redirect('home')
    
    if request.method == 'POST':
        u = request.POST.get('username')
        p = request.POST.get('password')
        user = authenticate(request, username=u, password=p)
        if user is not None:
            if user.is_active:
                login(request, user)
                # Redirect staff users to admin dashboard, others to home
                if user.is_staff:
                    return redirect('admin_dashboard')
                return redirect('home')
            else:
                messages.error(request, "Your account is inactive. Please contact an administrator.")
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

@csrf_exempt
@require_http_methods(["POST"])
def n8n_webhook_new_incident(request):
    """
    Webhook endpoint for n8n to send new incident data.
    Accepts POST requests with JSON payload from n8n.
    """
    try:
        # Parse JSON data from n8n
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            # Fallback to form data
            data = request.POST.dict()
        
        # Extract incident data from payload
        title = data.get('title', '')
        description = data.get('description', '')
        status = data.get('status', 'Open')
        
        # Get user - try by username, email, or user_id
        user = None
        if 'user_id' in data:
            try:
                user = User.objects.get(id=data['user_id'])
            except User.DoesNotExist:
                pass
        elif 'username' in data:
            try:
                user = User.objects.get(username=data['username'])
            except User.DoesNotExist:
                pass
        elif 'email' in data:
            try:
                user = User.objects.get(email=data['email'])
            except User.DoesNotExist:
                pass
        
        # If no user found, use a default user or return error
        if not user:
            # Try to get or create a default system user
            user, created = User.objects.get_or_create(
                username='system',
                defaults={'email': 'system@example.com'}
            )
        
        # Validate title word count (max 10 words)
        if title:
            title_words = title.strip().split()
            if len(title_words) > 10:
                return JsonResponse({
                    'success': False,
                    'error': 'Issue title cannot exceed 10 words.'
                }, status=400)
        
        # Create the incident
        incident = Incident(
            user=user,
            title=title or 'Incident from n8n',
            description=description or 'Reported via n8n webhook',
            status=status
        )
        
        # Try to populate from EmployeeProfile if available
        profile = getattr(user, 'employeeprofile', None)
        if profile:
            incident.laptop_model = profile.laptop_model
            incident.laptop_serial = profile.laptop_serial
            incident.department = profile.get_department_display()
        
        # Override with data from webhook if provided
        if 'laptop_model' in data:
            incident.laptop_model = data['laptop_model']
        if 'laptop_serial' in data:
            incident.laptop_serial = data['laptop_serial']
        if 'department' in data:
            incident.department = data['department']
        if 'reporter_name' in data:
            incident.reporter_name = data['reporter_name']
        if 'email' in data:
            incident.email = data['email']
        
        # Save the incident
        incident.save()
        
        # If status is Resolved, set resolved_at
        if status == 'Resolved':
            incident.resolved_at = incident.created_at
            incident.save()
        
        # Return success response
        return JsonResponse({
            'success': True,
            'incident_id': incident.id,
            'message': 'Incident created successfully',
            'ticket_id': incident.id,
            'title': incident.title,
            'status': incident.status,
            'reported_by_id': user.id,
            'reported_by': user.username,
            'user_id': user.id
        }, status=201)
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON payload'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def telegram_acknowledge(request, ticket_id):
    """
    Webhook endpoint for Telegram acknowledge button callback.
    Updates the incident to mark it as acknowledged by IT.
    """
    try:
        # Parse JSON data from Telegram callback
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST.dict()
        
        # Get the incident
        try:
            incident = Incident.objects.get(id=ticket_id)
        except Incident.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Incident not found'
            }, status=404)
        
        # Get IT user from callback data or use a default
        # In a real scenario, you'd identify the IT user from Telegram user ID
        it_user = None
        if 'telegram_user_id' in data:
            # You can map Telegram user IDs to Django users if needed
            # For now, we'll use the first staff user or create a system user
            it_user = User.objects.filter(is_staff=True).first()
        
        if not it_user:
            # Use first staff user or create system user
            it_user = User.objects.filter(is_staff=True).first()
            if not it_user:
                it_user, _ = User.objects.get_or_create(
                    username='it_system',
                    defaults={'email': 'it@example.com', 'is_staff': True}
                )
        
        # Update incident acknowledgment
        incident.it_acknowledged = True
        incident.it_acknowledged_at = timezone.now()
        incident.it_acknowledged_by = it_user
        # Change status to In Progress when acknowledged
        if incident.status == 'Open':
            incident.status = 'In Progress'
        incident.save()
        
        # Return success response
        return JsonResponse({
            'success': True,
            'message': f'Ticket #{ticket_id} acknowledged by IT',
            'ticket_id': ticket_id,
            'acknowledged_by': it_user.username,
            'acknowledged_at': incident.it_acknowledged_at.isoformat()
        }, status=200)
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON payload'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
def acknowledge_ticket(request, ticket_id):
    """
    Allow IT staff to acknowledge a ticket from the webapp.
    """
    if not request.user.is_staff:
        messages.error(request, "Only IT staff can acknowledge tickets.")
        return redirect('home')
    
    try:
        ticket = Incident.objects.get(id=ticket_id)
    except Incident.DoesNotExist:
        messages.error(request, "Ticket not found.")
        return redirect('admin_dashboard')
    
    # Update incident acknowledgment
    ticket.it_acknowledged = True
    ticket.it_acknowledged_at = timezone.now()
    ticket.it_acknowledged_by = request.user
    # Change status to In Progress when acknowledged
    if ticket.status == 'Open':
        ticket.status = 'In Progress'
    ticket.save()
    
    messages.success(request, f"Ticket #{ticket_id} acknowledged successfully.")
    return redirect('manage_ticket', ticket_id=ticket_id)

@login_required
def add_comment(request, ticket_id):
    """
    Allow all users to add comments to tickets.
    """
    try:
        ticket = Incident.objects.get(id=ticket_id)
    except Incident.DoesNotExist:
        messages.error(request, "Ticket not found.")
        if request.user.is_staff:
            return redirect('admin_dashboard')
        return redirect('home')
    
    # Check if user has permission to comment on this ticket
    # Users can comment on their own tickets, IT staff can comment on any ticket
    if not request.user.is_staff and ticket.user != request.user:
        messages.error(request, "You can only comment on your own tickets.")
        return redirect('home')
    
    if request.method == 'POST':
        message = request.POST.get('message', '').strip()
        if not message:
            messages.error(request, "Comment cannot be empty.")
        else:
            # Create the comment
            comment = Comment.objects.create(
                incident=ticket,
                user=request.user,
                message=message
            )
            # Mark comments as read for the user who posted (they just saw their own comment)
            CommentRead.objects.update_or_create(
                user=request.user,
                incident=ticket,
                defaults={'last_read_at': timezone.now()}
            )
            messages.success(request, "Comment added successfully. You can leave another comment if needed.")
    
    # Redirect back to the appropriate page
    if request.user.is_staff:
        return redirect('manage_ticket', ticket_id=ticket_id)
    else:
        return redirect('home')

@login_required
def mark_comments_read(request, ticket_id):
    """
    Mark comments as read for a specific ticket.
    Called when user views the ticket modal/details.
    """
    try:
        ticket = Incident.objects.get(id=ticket_id)
    except Incident.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Ticket not found'}, status=404)
    
    # Check if user has permission to view this ticket
    if not request.user.is_staff and ticket.user != request.user:
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    # Mark comments as read
    CommentRead.objects.update_or_create(
        user=request.user,
        incident=ticket,
        defaults={'last_read_at': timezone.now()}
    )
    
    return JsonResponse({'success': True})

@csrf_exempt
@require_http_methods(["POST"])
def update_ticket_response(request):
    """
    Improved API endpoint with error handling for n8n.
    """
    try:
        # 1. Safely parse JSON body
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False, 
            'error': 'Invalid JSON payload'
        }, status=400)

    # 2. Validate required keys
    ticket_id = data.get('ticket_id')
    if not ticket_id:
        return JsonResponse({
            'success': False, 
            'error': 'Missing ticket_id'
        }, status=400)

    try:
        # 3. Use your Incident model to find the ticket
        incident = Incident.objects.get(id=ticket_id)
        
        # Update fields based on your repository models
        incident.it_acknowledged = True
        incident.it_acknowledged_at = timezone.now()
        incident.status = 'In Progress'
        incident.save()
        
        return JsonResponse({
            'success': True, 
            'message': f'Ticket #{ticket_id} updated successfully'
        })
        
    except Incident.DoesNotExist:
        return JsonResponse({
            'success': False, 
            'error': f'Incident #{ticket_id} not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False, 
            'error': str(e)
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def telegram_leave_message(request, ticket_id):
    """
    Webhook endpoint for Telegram leave message button callback.
    Allows IT to leave a status message (e.g., waiting for parts, cannot finish, etc.).
    """
    try:
        # Parse JSON data from Telegram callback
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST.dict()
        
        # Get the incident
        try:
            incident = Incident.objects.get(id=ticket_id)
        except Incident.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Incident not found'
            }, status=404)
        
        # Get message from callback data
        message = data.get('message', '').strip()
        if not message:
            return JsonResponse({
                'success': False,
                'error': 'Message is required'
            }, status=400)
        
        # Get IT user from callback data or use a default
        it_user = None
        if 'telegram_user_id' in data:
            it_user = User.objects.filter(is_staff=True).first()
        
        if not it_user:
            it_user = User.objects.filter(is_staff=True).first()
            if not it_user:
                it_user, _ = User.objects.get_or_create(
                    username='it_system',
                    defaults={'email': 'it@example.com', 'is_staff': True}
                )
        
        # Update incident with message
        # Append to existing message if there is one
        if incident.it_status_message:
            incident.it_status_message = f"{incident.it_status_message}\n\n[{timezone.now().strftime('%d/%m/%Y %H:%M')}] {it_user.username}: {message}"
        else:
            incident.it_status_message = f"[{timezone.now().strftime('%d/%m/%Y %H:%M')}] {it_user.username}: {message}"
        
        # Mark as acknowledged if not already
        if not incident.it_acknowledged:
            incident.it_acknowledged = True
            incident.it_acknowledged_at = timezone.now()
            incident.it_acknowledged_by = it_user
            if incident.status == 'Open':
                incident.status = 'In Progress'
        
        incident.save()
        
        # Return success response
        return JsonResponse({
            'success': True,
            'message': f'Status message added to ticket #{ticket_id}',
            'ticket_id': ticket_id,
            'status_message': incident.it_status_message
        }, status=200)
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON payload'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def update_incident_from_n8n(request):
    """
    API endpoint for n8n to update ticket acknowledgment.
    Expects JSON payload: {"ticket_id": <number>, "response": "Acknowledged"}
    """
    try:
        # Parse JSON body
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error', 
            'message': 'Invalid JSON payload'
        }, status=400)
    
    # Validate ticket_id
    ticket_id = data.get('ticket_id')
    if not ticket_id:
        return JsonResponse({
            'status': 'error', 
            'message': "Field 'ticket_id' is required"
        }, status=400)
    
    # Convert to integer if it's a string
    try:
        if isinstance(ticket_id, str):
            ticket_id = int(ticket_id.strip())
        elif not isinstance(ticket_id, int):
            ticket_id = int(ticket_id)
    except (ValueError, TypeError):
        return JsonResponse({
            'status': 'error', 
            'message': f"Field 'ticket_id' must be a number, got: {type(ticket_id).__name__}"
        }, status=400)
    
    # Get the incident
    try:
        incident = Incident.objects.get(id=ticket_id)
    except Incident.DoesNotExist:
        return JsonResponse({
            'status': 'error', 
            'message': f'Incident #{ticket_id} not found'
        }, status=404)
    
    # Update the fields
    incident.it_acknowledged = True
    incident.it_acknowledged_at = timezone.now()
    if incident.status == 'Open':
        incident.status = 'In Progress'
    
    incident.save()
    
    return JsonResponse({
        'status': 'success', 
        'message': f'Ticket #{ticket_id} updated successfully',
        'ticket_id': ticket_id
    })

def _delete_user_sessions(user):
    """
    Helper function to delete all active sessions for a user.
    Returns tuple: (sessions_deleted, errors_list)
    """
    sessions_deleted = 0
    errors = []
    
    # Get all non-expired sessions
    all_sessions = Session.objects.filter(expire_date__gte=timezone.now())
    
    for session in all_sessions:
        try:
            # Decode session data
            session_data = session.get_decoded()
            session_user_id = session_data.get('_auth_user_id')
            
            # Check if this session belongs to the user
            # Compare as strings to handle both string and int IDs
            if session_user_id:
                # Convert both to strings for comparison
                if str(user.pk) == str(session_user_id):
                    session.delete()
                    sessions_deleted += 1
        except Exception as decode_error:
            # Some sessions might be corrupted or use different encoding
            # Log the error but continue processing other sessions
            errors.append({
                'session_key': session.session_key[:20] + '...' if session.session_key else 'unknown',
                'error': str(decode_error)
            })
            continue
    
    return sessions_deleted, errors

@csrf_exempt
@require_http_methods(["POST"])
def quarantine_user_api(request):
    """
    API endpoint for n8n to automatically quarantine a user when malware is detected.
    Kills all active sessions and deactivates the user account.
    Expects JSON payload: {"user_id": <number>}
    """
    try:
        # Parse JSON body
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error', 
            'message': 'Invalid JSON payload'
        }, status=400)
    
    # Validate user_id
    user_id = data.get('user_id')
    if not user_id:
        return JsonResponse({
            'status': 'error', 
            'message': "Field 'user_id' is required"
        }, status=400)
    
    # Convert to integer if it's a string
    try:
        if isinstance(user_id, str):
            user_id = int(user_id.strip())
        elif not isinstance(user_id, int):
            user_id = int(user_id)
    except (ValueError, TypeError):
        return JsonResponse({
            'status': 'error', 
            'message': f"Field 'user_id' must be a number, got: {type(user_id).__name__}"
        }, status=400)
    
    # Get the user
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return JsonResponse({
            'status': 'error', 
            'message': f'User ID {user_id} does not exist'
        }, status=404)
    
    # Quarantine the user: deactivate account and kill all sessions
    try:
        # 1. Deactivate the account - Use direct database update to ensure it persists
        was_active = user.is_active
        
        # Direct database update - this directly unchecks "Active" in Django admin
        User.objects.filter(pk=user_id).update(is_active=False)
        
        # Refresh the user object to get the updated value
        user.refresh_from_db()
        
        # Verify the update worked
        if user.is_active:
            # If still active, something is very wrong - log it
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f'CRITICAL: User {user_id} is_active is still True after direct update!')
            return JsonResponse({
                'status': 'error',
                'message': f'Failed to deactivate user {user_id} - database update failed'
            }, status=500)
        
        # 2. Clear all active sessions for this user
        sessions_deleted, decode_errors = _delete_user_sessions(user)
        
        # 3. Also clean up expired sessions (optional cleanup)
        expired_deleted = Session.objects.filter(expire_date__lt=timezone.now()).delete()[0]
        
        # Build response
        response_data = {
            'status': 'success', 
            'message': f'User ID {user_id} ({user.username}) has been quarantined successfully',
            'user_id': user_id,
            'username': user.username,
            'account_was_active': was_active,
            'account_now_active': user.is_active,  # Use actual value from DB
            'sessions_deleted': sessions_deleted,
            'expired_sessions_cleaned': expired_deleted
        }
        
        if decode_errors:
            response_data['warnings'] = f'{len(decode_errors)} sessions had decoding issues'
            response_data['decode_errors_count'] = len(decode_errors)
        
        return JsonResponse(response_data)
        
    except Exception as e:
        import traceback
        return JsonResponse({
            'status': 'error', 
            'message': f'Error quarantining user: {str(e)}',
            'traceback': traceback.format_exc() if settings.DEBUG else None
        }, status=500)

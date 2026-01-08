from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from .models import Incident
from datetime import datetime, timedelta, date
from django.utils import timezone

@login_required
def home(request):
    # Shows the user's own incident history
    incidents = Incident.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'home.html', {'incidents': incidents})

@login_required
def report_incident(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        # Providing a default value prevents the IntegrityError you saw earlier
        description = request.POST.get('description', 'Reported via Smart Scanner')
        status_value = request.POST.get('status', 'Open')

        Incident.objects.create(
            user=request.user,
            title=title,
            description=description,
            status=status_value
        )
        
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
                    from_date_obj = datetime.strptime(from_date, '%Y-%m-%d').date()
                else:
                    from_date_obj = from_date
                queryset = queryset.filter(created_at__date__gte=from_date_obj)
            if to_date:
                # Convert string to date object if needed
                if isinstance(to_date, str):
                    to_date_obj = datetime.strptime(to_date, '%Y-%m-%d').date()
                else:
                    to_date_obj = to_date
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
    
    context = {
        'incidents': incidents,
        'open_count': status_bar_base.filter(status='Open').count(),
        'resolved_count': status_bar_base.filter(status='Resolved').count(),
        'closed_count': status_bar_base.filter(status='Closed').count(),
        'open_year_count': Incident.objects.filter(status='Open', created_at__year=datetime.now().year).count(),
        'all_count': status_bar_base.count(),
        'period_filter': period_filter,  # Pass period to template
    }
    return render(request, 'admin_dashboard.html', context)
@login_required
def manage_ticket(request, ticket_id):
    if not request.user.is_staff:
        return redirect('home')
        
    ticket = Incident.objects.get(id=ticket_id)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        ticket.status = new_status
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
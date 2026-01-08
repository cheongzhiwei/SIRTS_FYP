from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q, Count
from .models import Incident, EmployeeProfile
from .forms import UserRegisterForm, IncidentForm, AdminTicketUpdateForm 
# (Assuming you have these forms defined. If not, I've handled the logic below generically)

# --- 1. AUTHENTICATION VIEWS ---

def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Account created for {user.username}!")
            return redirect('home')
    else:
        form = UserRegisterForm()
    return render(request, 'register.html', {'form': form})

def user_login(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                
                # Redirect Admins to Dashboard, Users to Home
                if user.is_superuser:
                    return redirect('admin_dashboard')
                else:
                    return redirect('home')
            else:
                messages.error(request, "Invalid username or password.")
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})

def user_logout(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('login')

# --- 2. USER VIEWS ---

@login_required
def home(request):
    """Shows the user their own ticket history."""
    tickets = Incident.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'home.html', {'tickets': tickets})


@login_required
def report_incident(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        # If description is empty, it will save as "No details provided"
        description = request.POST.get('description', 'No details provided')
        status_value = request.POST.get('status', 'Open')

        Incident.objects.create(
            user=request.user,
            title=title,
            description=description,
            status=status_value
        )
        # Success Message
        if status_value == 'Resolved':
            messages.success(request, "🎉 Great! Your issue is recorded as Self-Fixed.")
        else:
            messages.success(request, "Ticket submitted successfully. IT will review it shortly.")

        return redirect('home')

    return render(request, 'report_incident.html')

def is_admin(user):
    return user.is_superuser

@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    # 1. Base Query
    tickets = Incident.objects.all().order_by('-created_at')
    
    # --- 📊 CALCULATE STATS (5 BOXES) ---
    total_all = Incident.objects.count()
    count_open = Incident.objects.filter(status='Open').count()
    
    # ✅ FIX: Count ALL variations of "Self Fixed" / "Resolved"
    count_self_fixed = Incident.objects.filter(
        Q(status='Resolved') | 
        Q(status='Self Fixed') | 
        Q(status='Self-Fixed')
    ).count()
    
    count_closed = Incident.objects.filter(status='Closed').count()
    
    # Calculate "Open Tickets for This Year"
    current_year = timezone.now().year
    count_year_open = Incident.objects.filter(created_at__year=current_year, status='Open').count()

    # --- 🔍 FILTERING LOGIC ---
    
    # 1. Date Shortcuts (Default = 'week')
    date_filter = request.GET.get('date_range', 'week') 
    today = timezone.now().date()
    
    start_date = None
    if date_filter == 'today':
        start_date = today
    elif date_filter == 'week':
        start_date = today - timedelta(days=7)
    elif date_filter == 'month':
        start_date = today - timedelta(days=30)
    
    if start_date:
        tickets = tickets.filter(created_at__date__gte=start_date)

    # 2. Manual Date Picker
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    if date_from and date_to:
        tickets = tickets.filter(created_at__range=[date_from, date_to])

    # 3. Status Filter (✅ UPDATED LOGIC)
    status = request.GET.get('status')
    if status:
        # If the URL asks for "Resolved" (Blue Box), we fetch ALL variations
        if status == 'Resolved':
            tickets = tickets.filter(
                Q(status='Resolved') | 
                Q(status='Self Fixed') | 
                Q(status='Self-Fixed')
            )
        else:
            tickets = tickets.filter(status=status)

    # 4. Department Filter
    department = request.GET.get('department')
    if department:
        tickets = tickets.filter(department=department)

    # 5. Laptop Model Search
    laptop = request.GET.get('laptop')
    if laptop:
        tickets = tickets.filter(user__employeeprofile__laptop_model__icontains=laptop)

    # 6. Username Search
    reporter = request.GET.get('reporter')
    if reporter:
        tickets = tickets.filter(user__username__icontains=reporter)

    # --- 📝 PREPARE DROPDOWNS ---
    # Try/Except block in case EmployeeProfile doesn't exist yet
    try:
        dept_choices = EmployeeProfile.DEPARTMENT_CHOICES
    except AttributeError:
        dept_choices = [] # Fallback if model not ready

    context = {
        'tickets': tickets,
        'total_all': total_all,
        'count_open': count_open,
        'count_self_fixed': count_self_fixed, 
        'count_closed': count_closed,
        'count_year_open': count_year_open,
        'current_date_range': date_filter,
        'dept_choices': dept_choices,
    }
    return render(request, 'admin_dashboard.html', context)

@login_required
@user_passes_test(is_admin)
def manage_ticket(request, ticket_id):
    ticket = get_object_or_404(Incident, id=ticket_id)
    
    if request.method == 'POST':
        # Update Status
        new_status = request.POST.get('status')
        admin_note = request.POST.get('admin_note')
        
        if new_status:
            ticket.status = new_status
        if admin_note:
            # You might want to append notes or just overwrite
            ticket.admin_response = admin_note
            
        ticket.save()
        messages.success(request, f"Ticket #{ticket.id} updated successfully.")
        return redirect('admin_dashboard')

    return render(request, 'manage_ticket.html', {'ticket': ticket})
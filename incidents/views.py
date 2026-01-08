from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from .models import Incident
from datetime import datetime
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

    if status_filter:
        incidents = incidents.filter(status=status_filter)
    if user_filter:
        incidents = incidents.filter(user__username__icontains=user_filter)
    # Note: If you add a Laptop Model field later, filter it here

    # Summary Counts
    context = {
        'incidents': incidents,
        'open_count': Incident.objects.filter(status='Open').count(),
        'resolved_count': Incident.objects.filter(status='Resolved').count(),
        'closed_count': Incident.objects.filter(status='Closed').count(),
        'open_year_count': Incident.objects.filter(status='Open', created_at__year=datetime.now().year).count(),
        'all_count': Incident.objects.all().count(),
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
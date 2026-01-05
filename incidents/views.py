from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Incident

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
from django.db import models
from django.contrib.auth.models import User

# 1. EMPLOYEE PROFILE (Extends the User model)
class EmployeeProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    
    # Department List for Dropdowns
    DEPARTMENT_CHOICES = [
        ('IT', 'IT Support'),
        ('HR', 'Human Resources'),
        ('FIN', 'Finance'),
        ('MKT', 'Marketing'),
        ('OPS', 'Operations'),
        ('SAL', 'Sales'),
        ('EXEC', 'Management/Executive'),
    ]

    employee_name = models.CharField(max_length=100, null=True, blank=True)
    
    department = models.CharField(
        max_length=50, 
        choices=DEPARTMENT_CHOICES, 
        null=True, 
        blank=True
    )
    
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    laptop_model = models.CharField(max_length=100, blank=True, null=True)
    laptop_serial = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} Profile"

# 2. INCIDENT TICKET MODEL
class Incident(models.Model):

    # Link to the logged-in user
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    
    # Issue Details
    title = models.CharField(max_length=200)
    description = models.TextField()

    # ASSET HISTORY LEDGER FIELDS
    # We add these to "Snapshot" the hardware at the time of the report
    laptop_model = models.CharField(max_length=100, blank=True, null=True)
    laptop_serial = models.CharField(max_length=100, blank=True, null=True)
    department = models.CharField(max_length=100, blank=True, null=True)
    
    # Manual Reporting Fields (For when they type it in manually)
    reporter_name = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)

    # Status Options
    STATUS_CHOICES = [
        ('Open', 'Open'),
        ('In Progress', 'In Progress'),
        ('Resolved', 'Resolved'), # We treat 'Self Fixed' as Resolved in views
        ('Closed', 'Closed'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Open')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    # ✅ ADMIN RESPONSE FIELD (This fixes your error!)
    admin_response = models.TextField(blank=True, null=True)
    resolved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='resolved_incidents')

    def __str__(self):
        return f"{self.title} - {self.status}"

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    department = models.CharField(max_length=100, default='General')
    laptop_model = models.CharField(max_length=100, default='Unknown')

    def __str__(self):
        return f"{self.user.username}'s Profile"
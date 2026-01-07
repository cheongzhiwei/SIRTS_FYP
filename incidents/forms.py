from django import forms
from django.contrib.auth.models import User
from .models import Incident

# 1. USER REGISTRATION FORM
class UserRegisterForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ['username', 'email', 'password']

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password != confirm_password:
            raise forms.ValidationError("Passwords do not match")

# 2. INCIDENT REPORT FORM (Manual Entry)
class IncidentForm(forms.ModelForm):
    class Meta:
        model = Incident
        fields = ['reporter_name', 'department', 'email', 'title', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }

# 3. ADMIN UPDATE FORM (For Managing Tickets)
class AdminTicketUpdateForm(forms.ModelForm):
    class Meta:
        model = Incident
        fields = ['status', 'admin_response']
        widgets = {
            'admin_response': forms.Textarea(attrs={'rows': 3}),
        }
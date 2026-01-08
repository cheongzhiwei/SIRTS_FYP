from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import Incident, EmployeeProfile, UserProfile

# 1. Define the "Inline" for EmployeeProfile (The Profile Box)
# This says: "Put the EmployeeProfile form INSIDE the User form"
class EmployeeProfileInline(admin.StackedInline):
    model = EmployeeProfile
    can_delete = False
    verbose_name_plural = 'Employee Details'
    fields = ('department', 'laptop_model', 'laptop_serial', 'employee_name', 'phone_number')
    # Show the inline even if empty (allows creating profile on user creation)
    extra = 0
    min_num = 0
    max_num = 1

# 2. Define the "Inline" for UserProfile (Alternative Profile)
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'User Profile Details'
    fields = ('department', 'laptop_model')
    # Show the inline even if empty
    extra = 0
    min_num = 0
    max_num = 1

# 3. Define the new User Admin with inlines
class UserAdmin(BaseUserAdmin):
    # Add inlines - they will appear as separate sections below the user info
    # Using only EmployeeProfileInline as primary, add UserProfileInline if needed
    inlines = [EmployeeProfileInline]
    
    # 1. Define exactly which columns to show in the list view
    list_display = ('username', 'get_department', 'get_laptop_model', 'email', 'is_staff')

    # 2. Add Filters and Search (Optional but recommended)
    # Only filter by is_staff to avoid issues with missing relationships
    list_filter = ('is_staff',)
    search_fields = ('username', 'email')

    # 3. Helper function to fetch the Department from the Profile
    def get_department(self, obj):
        try:
            # Try EmployeeProfile first
            if hasattr(obj, 'employeeprofile'):
                profile = obj.employeeprofile
                if profile and profile.department:
                    return profile.get_department_display()
            # Fall back to UserProfile
            if hasattr(obj, 'userprofile'):
                profile = obj.userprofile
                if profile and profile.department:
                    return profile.department
        except Exception:
            pass
        return "-" # Returns a dash if they have no profile yet
    
    # Label the column header nicely
    get_department.short_description = 'Department'
    
    # 4. Helper function to fetch the Laptop Model from the Profile
    def get_laptop_model(self, obj):
        try:
            # Try EmployeeProfile first
            if hasattr(obj, 'employeeprofile'):
                profile = obj.employeeprofile
                if profile and profile.laptop_model:
                    return profile.laptop_model
            # Fall back to UserProfile
            if hasattr(obj, 'userprofile'):
                profile = obj.userprofile
                if profile and profile.laptop_model:
                    return profile.laptop_model
        except Exception:
            pass
        return "N/A" # Returns N/A if they have no laptop model
    
    # Label the column header nicely
    get_laptop_model.short_description = 'Laptop Model'

admin.site.unregister(User)
admin.site.register(User, UserAdmin)
admin.site.register(Incident)
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import Incident, EmployeeProfile

# 1. Define the "Inline" (The Profile Box)
# This says: "Put the EmployeeProfile form INSIDE the User form"
class EmployeeProfileInline(admin.StackedInline):
    model = EmployeeProfile
    can_delete = False
    verbose_name_plural = 'Employee Details'

# 2. Define the new User Admin
class UserAdmin(BaseUserAdmin):
    inlines = [EmployeeProfileInline]
    
    # 1. Define exactly which columns to show
    list_display = ('username', 'get_department', 'email')

    # 2. Add Filters and Search (Optional but recommended)
    list_filter = ('is_staff', 'employeeprofile__department')
    search_fields = ('username', 'email', 'employeeprofile__employee_name')

    # 3. Helper function to fetch the Department from the Profile
    def get_department(self, obj):
        try:
            # return obj.employeeprofile.department  <-- This shows the code "IT"
            return obj.employeeprofile.get_department_display() # <-- This shows "IT Support"
        except:
            return "-" # Returns a dash if they have no profile yet
    
    # Label the column header nicely
    get_department.short_description = 'Department'

admin.site.unregister(User)
admin.site.register(User, UserAdmin)
admin.site.register(Incident)
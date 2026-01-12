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

# 3. Define the "Inline" for Incident (Case Table)
class IncidentInline(admin.TabularInline):
    model = Incident
    fk_name = 'user'  # Specify which ForeignKey to use (the reporter, not resolved_by)
    verbose_name_plural = 'Cases / Incidents'
    fields = ('id', 'get_reporter_name', 'get_date_created', 'get_date_close', 'status')
    readonly_fields = ('id', 'get_reporter_name', 'get_date_created', 'get_date_close')
    can_delete = False
    extra = 0
    show_change_link = True
    
    def get_reporter_name(self, obj):
        """Get reporter name from user or reporter_name field"""
        if obj.reporter_name:
            return obj.reporter_name
        return obj.user.username
    get_reporter_name.short_description = 'Reporter Name'
    
    def get_date_created(self, obj):
        """Get date created formatted"""
        if obj.created_at:
            return obj.created_at.strftime('%d/%m/%Y %H:%M')
        return '-'
    get_date_created.short_description = 'Date Created'
    
    def get_date_close(self, obj):
        """Get date closed (resolved_at)"""
        if obj.resolved_at:
            return obj.resolved_at.strftime('%d/%m/%Y %H:%M')
        return '-'
    get_date_close.short_description = 'Date Close'
    
    def has_add_permission(self, request, obj=None):
        """Disable adding incidents from user admin page"""
        return False

# 4. Define the new User Admin with inlines
class UserAdmin(BaseUserAdmin):
    # Add inlines - they will appear as separate sections below the user info
    # IncidentInline shows all cases/incidents for this user
    inlines = [EmployeeProfileInline, IncidentInline]
    
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

# 5. Define custom Incident Admin
class IncidentAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_reporter_user', 'title', 'get_date_created', 'get_date_close', 'get_status_display')
    list_filter = ('status', 'created_at')  # Filters above the table
    search_fields = ('title', 'user__username', 'reporter_name', 'description')  # Search box above the table
    readonly_fields = ('created_at', 'resolved_at', 'resolved_by')
    
    # Remove actions dropdown
    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions
    
    actions = None  # Disable actions
    
    fieldsets = (
        ('Case Information', {
            'fields': ('user', 'reporter_name', 'title', 'description', 'status')
        }),
        ('Resolution Details', {
            'fields': ('admin_response', 'resolved_by', 'resolved_at'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def get_reporter_user(self, obj):
        """Get reporter user name"""
        if obj.reporter_name:
            return f"{obj.user.username} ({obj.reporter_name})"
        return obj.user.username
    get_reporter_user.short_description = 'Reporter User'
    get_reporter_user.admin_order_field = 'user__username'
    
    def get_date_created(self, obj):
        """Format date created"""
        if obj.created_at:
            return obj.created_at.strftime('%d/%m/%Y %H:%M')
        return '-'
    get_date_created.short_description = 'Date Created'
    get_date_created.admin_order_field = 'created_at'
    
    def get_date_close(self, obj):
        """Format date closed"""
        if obj.resolved_at:
            return obj.resolved_at.strftime('%d/%m/%Y %H:%M')
        return '-'
    get_date_close.short_description = 'Date Close'
    get_date_close.admin_order_field = 'resolved_at'
    
    def get_status_display(self, obj):
        """Custom status display: Open -> open, Resolved -> self-fixed, Closed -> close"""
        status_map = {
            'Open': 'open',
            'In Progress': 'open',
            'Resolved': 'self-fixed',
            'Closed': 'close'
        }
        return status_map.get(obj.status, obj.status.lower())
    get_status_display.short_description = 'Status'
    get_status_display.admin_order_field = 'status'

admin.site.unregister(User)
admin.site.register(User, UserAdmin)
admin.site.register(Incident, IncidentAdmin)
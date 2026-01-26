from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.contrib.admin import DateFieldListFilter
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.db.models import Q
from datetime import datetime, timedelta
from .models import Incident, EmployeeProfile, UserProfile, Comment, CommentRead

# Custom Date Range Filter
class DateRangeFilter(admin.SimpleListFilter):
    title = _('Date Created')
    parameter_name = 'created_at'

    def lookups(self, request, model_admin):
        return (
            ('today', _('Today')),
            ('week', _('Past 7 days')),
            ('month', _('This month')),
            ('year', _('This year')),
        )

    def queryset(self, request, queryset):
        if self.value() == 'today':
            today = timezone.now().date()
            return queryset.filter(created_at__date=today)
        elif self.value() == 'week':
            week_ago = timezone.now() - timedelta(days=7)
            return queryset.filter(created_at__gte=week_ago)
        elif self.value() == 'month':
            month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            return queryset.filter(created_at__gte=month_start)
        elif self.value() == 'year':
            year_start = timezone.now().replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            return queryset.filter(created_at__gte=year_start)
        return queryset

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

# 5. Define Inline Admins for Comments and CommentRead
class CommentInline(admin.TabularInline):
    model = Comment
    extra = 0
    readonly_fields = ('created_at',)
    fields = ('user', 'message', 'created_at')
    verbose_name = 'Comment'
    verbose_name_plural = 'Comments'
    can_delete = True
    ordering = ('created_at',)  # Earliest first
    
    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        # Make the message field smaller and more compact
        formset.form.base_fields['message'].widget.attrs.update({
            'rows': 2,
            'cols': 30,
            'style': 'width: 100%; max-width: 300px; height: 50px; resize: vertical; font-size: 12px;'
        })
        return formset

class CommentReadInline(admin.TabularInline):
    model = CommentRead
    extra = 0
    readonly_fields = ('user', 'last_read_at')
    fields = ('user', 'last_read_at')
    verbose_name = 'Comment Read'
    verbose_name_plural = 'Comment Read Status'
    can_delete = False  # Don't allow deleting (they're auto-managed)
    can_add = False  # Don't allow adding (they're auto-created)
    # Note: Don't set max_num = 0 as it prevents existing records from displaying

# 6. Define custom Incident Admin
class IncidentAdmin(admin.ModelAdmin):
    list_display = (
        'id', 
        'title', 
        'user', 
        'department', 
        'laptop_model', 
        'laptop_serial',  # The "Snapshot" serial number
        'status', 
        'created_at'
    )
    # Ensure 'user__username' is in search_fields so you can type the name in the search box
    search_fields = ('id', 'title', 'user__username', 'reporter_name', 'description', 'laptop_model', 'laptop_serial', 'department')
    # This makes the user selection a searchable dropdown instead of a long list
    autocomplete_fields = ['user']
    # Combined list_filter with all filters: user, status, laptop_model, and date filters
    list_filter = (
        ('created_at', DateFieldListFilter),
        'user',
        'status',
        'laptop_model',
        DateRangeFilter
    )
    readonly_fields = ('created_at', 'resolved_at', 'resolved_by')
    # Add inlines for Comments and CommentRead
    inlines = [CommentInline, CommentReadInline]

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}
        
        # Setting these to False removes the buttons from the bottom of the edit page
        extra_context['show_save_and_add_another'] = False
        extra_context['show_save_and_continue'] = False
        
        return super().change_view(
            request, object_id, form_url, extra_context=extra_context,
        )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        
        # Filter by reporter user (exact match for dropdown, or icontains for text input)
        user_filter = request.GET.get('user')
        if user_filter:
            # Try exact match first (for dropdown), then fall back to icontains (for text input)
            try:
                qs = qs.filter(user__id=user_filter)
            except (ValueError, TypeError):
                # If not a valid ID, treat as username search
                qs = qs.filter(user__username__icontains=user_filter)
        
        return qs
    
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        # Get all users who have reported incidents (for dropdown)
        users_with_incidents = User.objects.filter(incident__isnull=False).distinct().order_by('username')
        extra_context['users'] = users_with_incidents
        return super().changelist_view(request, extra_context)
    
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

# 7. Define Comment Admin (standalone - hidden from admin interface)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('id', 'incident', 'user', 'created_at', 'message_preview')
    list_filter = ('created_at', 'user', 'incident')
    search_fields = ('message', 'user__username', 'incident__title', 'incident__id')
    readonly_fields = ('created_at',)
    
    def message_preview(self, obj):
        """Show first 50 characters of message"""
        if len(obj.message) > 50:
            return obj.message[:50] + '...'
        return obj.message
    message_preview.short_description = 'Message Preview'
    
    def get_model_perms(self, request):
        # Hide from admin index but still allow direct access if needed
        return {}

# 8. Define CommentRead Admin (standalone - hidden from admin interface)
class CommentReadAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'incident', 'last_read_at')
    list_filter = ('last_read_at', 'user', 'incident')
    search_fields = ('user__username', 'incident__title', 'incident__id')
    readonly_fields = ('last_read_at',)
    
    def get_model_perms(self, request):
        # Hide from admin index but still allow direct access if needed
        return {}

admin.site.unregister(User)
admin.site.register(User, UserAdmin)
admin.site.register(Incident, IncidentAdmin)
# Register but hide from sidebar - they're accessible via Incident inline only
admin.site.register(Comment, CommentAdmin)
admin.site.register(CommentRead, CommentReadAdmin)
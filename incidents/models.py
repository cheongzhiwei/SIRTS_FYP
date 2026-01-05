from django.db import models
from django.contrib.auth.models import User

class Incident(models.Model):
    # Link the ticket to the Staff Member who reported it
    reporter = models.ForeignKey(User, on_delete=models.CASCADE)
    
    # The actual data
    title = models.CharField(max_length=200)
    description = models.TextField()
    
    # Auto-add the date and status
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default='Open') # Open, Closed, Pending

    def __str__(self):
        return f"{self.title} - {self.reporter.username}"
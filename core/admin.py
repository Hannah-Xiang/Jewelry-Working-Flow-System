from django.contrib import admin

from .models import Customer, JobType, Status, Ticket

# Register your models here.

admin.site.register(Customer)
admin.site.register(JobType)
admin.site.register(Status)
admin.site.register(Ticket)

from django.contrib import admin

from .models import Customer, JobType, Status, Ticket, TicketPhoto

# Register your models here.

admin.site.register(Customer)
admin.site.register(JobType)
admin.site.register(Status)

class TicketPhotoInline(admin.TabularInline):
    model = TicketPhoto
    extra = 0
    readonly_fields = ["uploaded_at"]


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ["ticket_number", "customer", "job_type", "status", "due_date"]
    inlines = [TicketPhotoInline]


admin.site.register(TicketPhoto)
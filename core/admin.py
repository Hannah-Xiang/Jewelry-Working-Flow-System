from django.contrib import admin

from .models import Customer, JobType, Note, Status, Ticket, TicketPhoto, StatusHistory, AuditLog

# Register your models here.

admin.site.register(Customer)
admin.site.register(JobType)
admin.site.register(Status)
admin.site.register(Note)
admin.site.register(StatusHistory)
@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "user",
        "action",
        "model_name",
        "object_id",
        "description",
    )

    list_filter = (
        "action",
        "model_name",
        "user",
    )

    search_fields = (
        "user__username",
        "description",
        "object_id",
    )

    readonly_fields = (
        "created_at",
    )

class TicketPhotoInline(admin.TabularInline):
    model = TicketPhoto
    extra = 0
    readonly_fields = ["uploaded_at"]


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ["ticket_number", "customer", "job_type", "status", "due_date"]
    inlines = [TicketPhotoInline]


admin.site.register(TicketPhoto)
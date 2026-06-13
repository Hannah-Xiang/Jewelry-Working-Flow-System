from django.shortcuts import render
from .models import Status, Ticket
from datetime import timedelta
from django.utils import timezone

# Create your views here.

from datetime import timedelta
from django.utils import timezone
from .models import Ticket

def dashboard(request):

    today = timezone.now().date()

    # Monday of current week
    start_of_week = today - timedelta(days=today.weekday())

    # Sunday of current week
    end_of_week = start_of_week + timedelta(days=6)

    # Recent tickets (last 3 months)
    three_months_ago = today - timedelta(days=90)

    recent_tickets = Ticket.objects.filter(
        created_date__gte=three_months_ago
    ).order_by('-created_date')[:10]

    # OPEN JOBS
    # Everything not completed
    open_jobs = Ticket.objects.exclude(
        status__status="Completed"
    ).count()

    # DUE THIS WEEK
    due_this_week = Ticket.objects.filter(
        due_date__range=(start_of_week, end_of_week)
    ).exclude(
        status__status="Completed"
    ).count()

    # READY FOR PICKUP
    ready_for_pickup = Ticket.objects.filter(
        status__status="Ready for Pickup"
    ).count()

    # OVERDUE
    overdue = Ticket.objects.filter(
        due_date__lt=today
    ).exclude(
        status__status="Completed"
    ).count()

    status_summary = []

    for status in Status.objects.all():

        count = Ticket.objects.filter(
            status=status
        ).count()

        status_summary.append({
            "name": status.status,
            "count": count,
            "color": status.color
        })

    
    today = timezone.now().date()

    upcoming_due_dates = Ticket.objects.filter(
        due_date__gte=today
    ).exclude(
        status__status="Completed"
    ).order_by(
        'due_date'
    )[:5]

    context = {
        "recent_tickets": recent_tickets,
        "open_jobs": open_jobs,
        "due_this_week": due_this_week,
        "ready_for_pickup": ready_for_pickup,
        "overdue": overdue,
        "status_summary": status_summary,
        "upcoming_due_dates": upcoming_due_dates,
    }

    return render(request, "core/dashboard.html", context)

def new_ticket(request):
    return render(request, 'core/new_ticket.html')

def all_tickets(request):
    return render(request, 'core/all_tickets.html')

def calendar(request):
    return render(request, 'core/calendar.html')

def customers(request):
    return render(request, 'core/customers.html')

def base(request):
    return render(request, 'core/base.html')

from django.shortcuts import render
from .models import Status, Ticket, JobType, Customer
from datetime import timedelta
from django.utils import timezone
from django.db.models import Q
from django.http import JsonResponse



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

    tickets = Ticket.objects.select_related(
        'customer',
        'job_type',
        'status'
    ).order_by('-created_date')

    search = request.GET.get('search')
    status_id = request.GET.get('status')
    job_type_id = request.GET.get('job_type')

    if search:

        tickets = tickets.filter(

            Q(ticket_number__icontains=search)

            |

            Q(customer__name__icontains=search)

            |

            Q(customer__phone__icontains=search)

        )

    if status_id:

        tickets = tickets.filter(
            status_id=status_id
        )

    if job_type_id:

        tickets = tickets.filter(
            job_type_id=job_type_id
        )

    context = {

        "tickets": tickets,

        "statuses": Status.objects.all(),

        "job_types": JobType.objects.all(),

        "ticket_count": tickets.count(),

        "selected_status": status_id,

        "selected_job_type": job_type_id,

        "search": search or ""

    }

    return render(
        request,
        "core/all_tickets.html",
        context
    )


def ticket_search(request):

    search = request.GET.get('search', '')
    status = request.GET.get('status', '')
    job_type = request.GET.get('job_type', '')

    tickets = Ticket.objects.select_related(
        'customer',
        'job_type',
        'status'
    ).order_by('-created_date')

    if search:

        tickets = tickets.filter(

            Q(ticket_number__icontains=search)

            |

            Q(customer__name__icontains=search)

            |

            Q(customer__phone__icontains=search)

        )

    if status:

        tickets = tickets.filter(
            status_id=status
        )

    if job_type:

        tickets = tickets.filter(
            job_type_id=job_type
        )

    data = []

    for ticket in tickets:

        data.append({

            "ticket_number":
                ticket.ticket_number,

            "customer":
                ticket.customer.name,

            "phone":
                ticket.customer.phone,

            "job_type":
                ticket.job_type.type,

            "status":
                ticket.status.status,

            "status_color":
                ticket.status.color,

            "due_date":
                ticket.due_date.strftime(
                    "%b %d, %Y"
                ),

            "created_date":
                ticket.created_date.strftime(
                    "%b %d, %Y"
                )

        })

    return JsonResponse({
        "tickets": data,
        "count": len(data)
    })


def calendar(request):
    return render(request, 'core/calendar.html')

def customers(request):
    return render(request, 'core/customers.html')

def base(request):
    return render(request, 'core/base.html')

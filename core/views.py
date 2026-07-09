from django.shortcuts import render
from .models import Status, Ticket, JobType, Customer
from datetime import timedelta
from django.utils import timezone
from django.db.models import Q
from django.http import JsonResponse
import calendar as pycalendar
from datetime import date
from django.shortcuts import get_object_or_404
import json
from datetime import date

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.db.models import Q

from .models import (
    Ticket,
    Customer,
    JobType,
    Status,
    TicketPhoto,
)

from .forms import TicketForm

from .utils import (
    generate_ticket_number,
    calculate_due_date,
    get_or_create_customer,
)



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
        due_date__lte=end_of_week
    ).exclude(
        status__status__in=[
            "Completed",
            "Ready for Pickup"
        ]
    ).count()

    # READY FOR PICKUP
    ready_for_pickup = Ticket.objects.filter(
        status__status="Ready for Pickup"
    ).count()

    # OVERDUE
    overdue = Ticket.objects.filter(
        due_date__lt=today
    ).exclude(
        status__status__in=[
            "Completed",
            "Ready for Pickup"
        ]
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

    if request.method == "POST":

        form = TicketForm(request.POST, request.FILES)

        if form.is_valid():

            existing_customer_id = request.POST.get("existing_customer_id")

            if existing_customer_id:
                # a customer was picked from the search dropdown -> reuse that record
                customer = Customer.objects.get(pk=existing_customer_id)
            else:
                # no customer picked -> fall back to your existing lookup/create logic
                customer = get_or_create_customer(
                    form.cleaned_data["customer_name"],
                    form.cleaned_data["phone"],
                    form.cleaned_data["email"]
                )

            ticket = form.save(commit=False)

            ticket.customer = customer

            ticket.save()

            # 保存图片
            photos = request.FILES.getlist("photos")

            for photo in photos:
                TicketPhoto.objects.create(
                    ticket=ticket,
                    image=photo
                )

            return redirect("all_tickets")

    else:

        form = TicketForm(
            initial={
                "ticket_number": generate_ticket_number(),
                "due_date": date.today()
            }
        )

    return render(
        request,
        "core/new_ticket.html",
        {
            "form": form,
            "today": date.today(),
            "job_types": JobType.objects.all(),
            "statuses": Status.objects.filter(status__in=["Received", "In Progress"]),
        }
    )
def customer_search(request):

    keyword = request.GET.get("q", "").strip()

    customers = Customer.objects.filter(

        Q(name__icontains=keyword) |
        Q(phone__icontains=keyword)

    )[:10]

    data = []

    for customer in customers:

        data.append({

    "id": customer.id,

    "name": customer.name,

    "phone": customer.phone,

    "email": customer.email,

    "ticket_count": customer.tickets.count(),

})

    return JsonResponse(data, safe=False)

def customer_detail(request, pk):

    customer = get_object_or_404(
        Customer,
        pk=pk
    )

    return JsonResponse({

        "id": customer.id,

        "name": customer.name,

        "phone": customer.phone,

        "email": customer.email,

    })

def jobtype_detail(request, pk):

    job_type = get_object_or_404(
        JobType,
        pk=pk
    )

    due_date = calculate_due_date(job_type)

    return JsonResponse({

        "duration": job_type.duration,

        "due_date": due_date.strftime("%Y-%m-%d")

    })

def generate_ticket(request):

    return JsonResponse({

        "ticket_number": generate_ticket_number()

    })

def all_tickets(request):
    

    tickets = Ticket.objects.select_related(
        'customer',
        'job_type',
        'status'
    ).order_by('-created_date')

    search = request.GET.get('search')
    status_id = request.GET.get('status')
    job_type_id = request.GET.get('job_type')
    open_jobs = request.GET.get("open")
    due = request.GET.get("due")
    pickup = request.GET.get("pickup")
    overdue = request.GET.get("overdue")
    

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
    if open_jobs:

        tickets = tickets.exclude(
            status__status="Completed"
        )
    if due == "thisweek":

        today = timezone.now().date()

        start_of_week = today - timedelta(
            days=today.weekday()
        )

        end_of_week = start_of_week + timedelta(days=6)

        tickets = tickets.filter(
            due_date__lte=end_of_week
        ).exclude(
            status__status__in=[
                "Completed",
                "Ready for Pickup"
            ]
        )
    
    if pickup:

        tickets = tickets.filter(
            status__status="Ready for Pickup"
        )
    
    if overdue:

        today = timezone.now().date()

        tickets = tickets.filter(
            due_date__lt=today
        ).exclude(
            status__status__in=[
                "Completed",
                "Ready for Pickup"
            ]
        )

    context = {

        "tickets": tickets,

        "statuses": Status.objects.all(),

        "job_types": JobType.objects.all(),

        "ticket_count": tickets.count(),

        "selected_status": status_id,

        "selected_job_type": job_type_id,

        "search": search or "",
        "today": timezone.now().date(),

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

            "id":
                ticket.id,

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
                ),

            

        })

    return JsonResponse({
        "tickets": data,
        "count": len(data)
    })


def calendar(request):

    today = timezone.now().date()

    # Current viewing month/year
    month = int(request.GET.get("month", today.month))
    year = int(request.GET.get("year", today.year))

    pycalendar.setfirstweekday(pycalendar.SUNDAY)
    cal = pycalendar.monthcalendar(year, month)

    tickets = Ticket.objects.select_related(
        "customer",
        "status",
        "job_type",
    ).filter(
        due_date__year=year,
        due_date__month=month,
    )

    tickets_by_day = {}
    tickets_json = {}

    for ticket in tickets:

        day = ticket.due_date.day

        tickets_by_day.setdefault(day, []).append(ticket)

        tickets_json.setdefault(day, []).append({
            "id": ticket.id,
            "ticket_number": ticket.ticket_number,
            "customer": ticket.customer.name,
            "job_type": ticket.job_type.type,
            "status": ticket.status.status,
            "color": ticket.status.color,
        })

    # Previous month
    if month == 1:
        prev_month = 12
        prev_year = year - 1
    else:
        prev_month = month - 1
        prev_year = year

    # Next month
    if month == 12:
        next_month = 1
        next_year = year + 1
    else:
        next_month = month + 1
        next_year = year

    months = [
        "January", "February", "March", "April",
        "May", "June", "July", "August",
        "September", "October", "November", "December"
    ]

    context = {

        # Calendar
        "calendar_weeks": cal,
        "tickets_by_day": tickets_by_day,

        # JSON for JavaScript
        "tickets_json": json.dumps(tickets_json),

        # Current viewing month
        "month": month,
        "year": year,
        "month_name": months[month - 1],

        # Month picker
        "months": months,
        "years": range(today.year - 5, today.year + 6),

        # Previous/next buttons
        "prev_month": prev_month,
        "prev_year": prev_year,
        "next_month": next_month,
        "next_year": next_year,

        # Today
        "today": today.day,
        "today_month": today.month,
        "today_year": today.year,

        # Only highlight today if viewing current month
        "is_current_month": (
            month == today.month and
            year == today.year
        ),
    }

    return render(
        request,
        "core/calendar.html",
        context,
    )

def ticket_detail(request, ticket_id):

    ticket = get_object_or_404(
        Ticket,
        id=ticket_id
    )

    context = {
        "ticket": ticket,
        "statuses": Status.objects.all()
    }

    return render(
        request,
        "core/ticket_detail.html",
        context
    )



from django.db.models import Count, Sum

def customers(request):

    customers = Customer.objects.annotate(
        job_count=Count("tickets")
    ).order_by("name")

    customer_id = request.GET.get("customer")

    if customer_id:
        customer = Customer.objects.get(id=customer_id)
    else:
        customer = customers.first()

    tickets = Ticket.objects.filter(
        customer=customer
    ).select_related(
        "status",
        "job_type"
    ).order_by("-created_date")

    total_value = (
        tickets.aggregate(
            Sum("price")
        )["price__sum"] or 0
    )

    context = {
        "customers": customers,
        "customer": customer,
        "tickets": tickets,
        "job_count": tickets.count(),
        "total_value": total_value,
    }

    return render(
        request,
        "core/customers.html",
        context,
    )

def base(request):
    return render(request, 'core/base.html')


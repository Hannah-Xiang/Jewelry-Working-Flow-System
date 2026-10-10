from asyncio.log import logger

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.db.models import Q, Count, Sum, OuterRef, Subquery
from datetime import timedelta, date
from django.utils import timezone
import calendar as pycalendar
import json
from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth.views import PasswordResetConfirmView
from django.urls import reverse_lazy
from django.contrib.auth.views import PasswordResetConfirmView
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.db.models import IntegerField
from django.db.models.functions import Substr, Cast
from .models import (
    Mold,
    Ticket,
    Customer,
    JobType,
    Status,
    TicketPhoto,
    Note,
    StatusHistory,
    AuditLog,
    MoldTag,
    MoldType,
)
import logging
from .forms import CustomerForm, TicketForm

from .utils import (
    generate_ticket_number,
    calculate_due_date,
    get_or_create_customer,
)

def create_audit_log(request, action, model_name, object_id="", description=""):
    AuditLog.objects.create(
        user=request.user if request.user.is_authenticated else None,
        action=action,
        model_name=model_name,
        object_id=str(object_id),
        description=description,
    )

@login_required
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
        ).annotate(
            latest_note_content=Subquery(
                Note.objects.filter(
                    ticket=OuterRef("pk")
                ).order_by("-created_at").values("content")[:1]
            )
        ).select_related(
            "customer",
            "job_type",
            "status"
        ).order_by(
            "-created_date"
        )[:10]

    # OPEN JOBS
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
        count = Ticket.objects.filter(status=status).count()

        status_summary.append({
            "name": status.status,
            "count": count,
            "color": status.color,
        })

    # Find the largest count
    max_count = max(
        [item["count"] for item in status_summary],
        default=1
    )

    # Calculate proportional height for each bar
    for item in status_summary:
        item["height"] = max(
            20,
            int(item["count"] / max_count * 160)
        )

    upcoming_due_dates = Ticket.objects.filter(
        due_date__gte=today
    ).exclude(
        status__status="Completed"
    ).order_by('due_date')[:5]

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

@login_required
def new_ticket(request):


    if request.method == "POST":

        form = TicketForm(request.POST, request.FILES)

        if form.is_valid():

            existing_customer_id = request.POST.get("existing_customer_id")

            if existing_customer_id:
                customer = Customer.objects.get(pk=existing_customer_id)
            else:
                customer = get_or_create_customer(
                    form.cleaned_data["customer_name"],
                    form.cleaned_data["phone"],
                    form.cleaned_data["email"]
                )

            ticket = form.save(commit=False)
            ticket.customer = customer
            ticket.save()
            create_audit_log(
                request,
                "CREATE",
                "Ticket",
                ticket.ticket_number,
                f"Created ticket {ticket.ticket_number}."
            )

            # record the starting point on the timeline
            StatusHistory.objects.create(
                ticket=ticket,
                status=ticket.status,
                note="Ticket created."
            )

            photos = request.FILES.getlist("photos")
            for photo in photos:
                ticket_photo = TicketPhoto.objects.create(
                    ticket=ticket,
                    image=photo
                )
                create_audit_log(
                    request,
                    "CREATE",
                    "TicketPhoto",
                    ticket_photo.id,
                    f"Created photo for ticket {ticket.ticket_number}."
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

@login_required
def delete_ticket(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)

    if request.method == "POST":
        ticket_number = ticket.ticket_number
        ticket.delete()
        create_audit_log(
        request,
        "DELETE",
        "Ticket",
        ticket_number,
        f"Deleted ticket {ticket_number}."
    )
        messages.success(request, "Ticket deleted successfully.")
        return redirect("all_tickets")

    return redirect("ticket_detail", ticket_id=ticket.id)

from django.db.models import Q

@login_required
def customer_search(request):

    keyword = request.GET.get("q", "").strip()
    page_number = request.GET.get("page", 1)

    # --------------------------------
    # Search customers
    # --------------------------------
    if keyword == "":
        customers = Customer.objects.all().order_by("name")

    else:

        # Normalize phone search input
        phone_digits = "".join(
            character for character in keyword
            if character.isdigit()
        )

        from django.db.models import Value
        from django.db.models.functions import Replace

        # Normalize phone number stored in database
        normalized_phone = Replace(
            Replace(
                Replace(
                    Replace(
                        "phone",
                        Value(" "),
                        Value("")
                    ),
                    Value("("),
                    Value("")
                ),
                Value(")"),
                Value("")
            ),
            Value("-"),
            Value("")
        )

        search_conditions = (
            Q(name__icontains=keyword) |
            Q(email__icontains=keyword) |
            Q(tickets__ticket_number__icontains=keyword)
        )

        if phone_digits:
            search_conditions |= Q(
                normalized_phone__icontains=phone_digits
            )

        customers = Customer.objects.annotate(
            normalized_phone=normalized_phone
        ).filter(
            search_conditions
        ).distinct().order_by("name")

    # --------------------------------
    # Pagination
    # --------------------------------
    paginator = Paginator(customers, 10)

    page_obj = paginator.get_page(page_number)

    # --------------------------------
    # Return JSON
    # --------------------------------
    data = []

    for customer in page_obj:

        data.append({
            "id": customer.id,
            "name": customer.name,
            "phone": customer.phone,
            "email": customer.email,
            "ticket_count": customer.tickets.count(),
        })

    return JsonResponse({
        "customers": data,
        "count": paginator.count,
        "page": page_obj.number,
        "num_pages": paginator.num_pages,
        "has_previous": page_obj.has_previous(),
        "has_next": page_obj.has_next(),
    })

@login_required
def customer_live_search(request):
    """
    Combined name + phone live search used by the New Ticket page.

    - name and phone both given  -> AND match (must match both)
    - only name given            -> filter by name only
    - only phone given           -> filter by phone only
    - neither given               -> return an empty list
    """

    name = request.GET.get("name", "").strip()
    phone = request.GET.get("phone", "").strip()

    if not name and not phone:
        return JsonResponse([], safe=False)

    customers = Customer.objects.all()

    if name:
        customers = customers.filter(name__icontains=name)

    if phone:
        customers = customers.filter(phone__icontains=phone)

    customers = customers[:10]

    data = []
    for customer in customers:

        created_date = getattr(customer, "created_date", None)

        data.append({
            "id": customer.id,
            "name": customer.name,
            "phone": customer.phone,
            "email": customer.email,
            "ticket_count": customer.tickets.count(),
            "created_date": created_date.isoformat() if created_date else None,
        })

    return JsonResponse(data, safe=False)

@login_required
def add_customer(request):

    if request.method == "POST":

        form = CustomerForm(request.POST)

        if form.is_valid():
            

            customer = form.save()

            create_audit_log(
        request,
        "CREATE",
        "Customer",
        customer.id,
        f"Created customer {customer.name} ({customer.phone})."
    )

            return redirect(f"/customers/?customer={customer.id}")

        # Form is invalid → show the page again
        customers = Customer.objects.annotate(
            job_count=Count("tickets")
        ).order_by("name")

        context = {
            "customers": customers,
            "customer_form": form,      # IMPORTANT: use the invalid form
            "show_form": True,
        }

        return render(request, "core/customers.html", context)

    return redirect("customers")
@login_required
def edit_customer(request, pk):

    customer = get_object_or_404(Customer, pk=pk)

    if request.method == "POST":

        form = CustomerForm(
            request.POST,
            instance=customer
        )

        if form.is_valid():

            form.save()
            create_audit_log(
        request,
        "UPDATE",
        "Customer",
        customer.id,
        f"Updated customer {customer.name} ({customer.phone})."
    )

            return redirect(
                f"{reverse('customers')}?customer={customer.id}"
            )

    else:

        form = CustomerForm(instance=customer)

    customers = Customer.objects.all().order_by("name")

    context = {
        "customers": customers,
        "customer": customer,
        "customer_form": form,
        "show_form": True,
        "is_edit": True,
    }

    return render(
        request,
        "core/customers.html",
        context,
    )

@login_required
def customer_detail(request, pk):

    customer = get_object_or_404(Customer, pk=pk)

    return JsonResponse({
        "id": customer.id,
        "name": customer.name,
        "phone": customer.phone,
        "email": customer.email,
    })

@login_required
def jobtype_detail(request, pk):

    job_type = get_object_or_404(JobType, pk=pk)
    due_date = calculate_due_date(job_type)

    return JsonResponse({
        "duration": job_type.duration,
        "due_date": due_date.strftime("%Y-%m-%d")
    })

@login_required
def generate_ticket(request):
    return JsonResponse({"ticket_number": generate_ticket_number()})

@login_required
def all_tickets(request):

    tickets = Ticket.objects.select_related(
        'customer', 'job_type', 'status'
    )

    search = request.GET.get('search')
    sort = request.GET.get('sort', 'created_date')
    direction = request.GET.get('direction', 'desc')

    # --------------------------------
    # Sorting
    # --------------------------------

    allowed_sorts = {
        'ticket_number': 'ticket_number',
        'customer': 'customer__name',
        'job_type': 'job_type__type',
        'status': 'status__status',
        'due_date': 'due_date',
        'created_date': 'created_date',
    }

    sort_field = allowed_sorts.get(sort, 'created_date')

    if direction == 'asc':
        tickets = tickets.order_by(sort_field, 'id')
    else:
        direction = 'desc'
        tickets = tickets.order_by(f'-{sort_field}', '-id')
    status_id = request.GET.get('status')
    job_type_id = request.GET.get('job_type')
    open_jobs = request.GET.get("open")
    due = request.GET.get("due")
    pickup = request.GET.get("pickup")
    overdue = request.GET.get("overdue")

    if search:
        tickets = tickets.filter(
            Q(ticket_number__icontains=search) |
            Q(customer__name__icontains=search) |
            Q(customer__phone__icontains=search)
        )

    if status_id:
        tickets = tickets.filter(status_id=status_id)

    if job_type_id:
        tickets = tickets.filter(job_type_id=job_type_id)

    if open_jobs:
        tickets = tickets.exclude(status__status="Completed")

    if due == "thisweek":
        today = timezone.now().date()
        start_of_week = today - timedelta(days=today.weekday())
        end_of_week = start_of_week + timedelta(days=6)

        tickets = tickets.filter(
            due_date__lte=end_of_week
        ).exclude(
            status__status__in=["Completed", "Ready for Pickup"]
        )

    if pickup:
        tickets = tickets.filter(status__status="Ready for Pickup")

    if overdue:
        today = timezone.now().date()
        tickets = tickets.filter(
            due_date__lt=today
        ).exclude(
            status__status__in=["Completed", "Ready for Pickup"]
        )
        # --------------------------------
    # Ticket pagination
    # --------------------------------
    paginator = Paginator(tickets, 10)

    page_number = request.GET.get("page")

    tickets = paginator.get_page(page_number)
    context = {
        "tickets": tickets,
        "statuses": Status.objects.all(),
        "job_types": JobType.objects.all(),
        "ticket_count": paginator.count,
        "selected_status": status_id,
        "selected_job_type": job_type_id,
        "search": search or "",
        "today": timezone.now().date(),

        # Sorting
        "sort": sort,
        "direction": direction,
    }

    return render(request, "core/all_tickets.html", context)

@login_required
def ticket_search(request):

    search = request.GET.get('search', '').strip()
    status = request.GET.get('status', '')
    job_type = request.GET.get('job_type', '')
    page_number = request.GET.get('page', 1)

    sort = request.GET.get('sort', 'created_date')
    direction = request.GET.get('direction', 'desc')

    # Dashboard filters
    open_jobs = request.GET.get("open")
    due = request.GET.get("due")
    pickup = request.GET.get("pickup")
    overdue = request.GET.get("overdue")

    tickets = Ticket.objects.select_related(
        'customer', 'job_type', 'status'
    )

    # --------------------------------
    # Search
    # --------------------------------
    if search:

        # Normalize phone search input
        phone_digits = "".join(
            character for character in search
            if character.isdigit()
        )

        # Normalize phone number stored in database
        from django.db.models import Value
        from django.db.models.functions import Replace

        normalized_phone = Replace(
            Replace(
                Replace(
                    Replace(
                        "customer__phone",
                        Value(" "),
                        Value("")
                    ),
                    Value("("),
                    Value("")
                ),
                Value(")"),
                Value("")
            ),
            Value("-"),
            Value("")
        )

        # Build search conditions
        search_conditions = (
            Q(ticket_number__icontains=search) |
            Q(customer__name__icontains=search)
        )

        # Phone search
        if phone_digits:
            search_conditions |= Q(
                normalized_phone__icontains=phone_digits
            )

        tickets = tickets.annotate(
            normalized_phone=normalized_phone
        ).filter(
            search_conditions
        )

    # --------------------------------
    # Status filter
    # --------------------------------
    if status:
        tickets = tickets.filter(
            status_id=status
        )

    # --------------------------------
    # Job type filter
    # --------------------------------
    if job_type:
        tickets = tickets.filter(
            job_type_id=job_type
        )
    # --------------------------------
    # Dashboard filters
    # --------------------------------

    if open_jobs:
        tickets = tickets.exclude(
            status__status="Completed"
        )

    if due == "thisweek":

        today = timezone.now().date()

        start_of_week = (
            today -
            timedelta(days=today.weekday())
        )

        end_of_week = (
            start_of_week +
            timedelta(days=6)
        )

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


    # --------------------------------
    # Sorting
    # --------------------------------

    allowed_sorts = {
        'ticket_number': 'ticket_number',
        'customer': 'customer__name',
        'job_type': 'job_type__type',
        'status': 'status__status',
        'due_date': 'due_date',
        'created_date': 'created_date',
    }

    sort_field = allowed_sorts.get(
        sort,
        'created_date'
    )

    if direction == 'asc':
        tickets = tickets.order_by(sort_field, 'id')
    else:
        direction = 'desc'
        tickets = tickets.order_by(
            f'-{sort_field}',
            '-id'
        )


    # --------------------------------
    # Ticket pagination
    # --------------------------------
    paginator = Paginator(tickets, 10)

    page_obj = paginator.get_page(page_number)

    # --------------------------------
    # Return JSON
    # --------------------------------
    data = []

    for ticket in page_obj:

        latest_note = ticket.notes.order_by("-created_at").first()

        data.append({
            "id": ticket.id,
            "ticket_number": ticket.ticket_number,
            "customer": ticket.customer.name,
            "phone": ticket.customer.phone,
            "job_type": ticket.job_type.type,
            "status": ticket.status.status,
            "status_color": ticket.status.color,
            "due_date": ticket.due_date.strftime("%b %d, %Y"),
            "created_date": ticket.created_date.strftime("%b %d, %Y"),
            "is_overdue": (
                ticket.due_date < timezone.now().date()
                and ticket.status.status != "Completed"
            ),
            "is_starred": ticket.is_starred,

            # Latest note for starred ticket
            "latest_note": (
                latest_note.content
                if ticket.is_starred and latest_note
                else ""
            ),
        })

    return JsonResponse({
        "tickets": data,
        "count": paginator.count,
        "page": page_obj.number,
        "num_pages": paginator.num_pages,
        "has_previous": page_obj.has_previous(),
        "has_next": page_obj.has_next(),
    })

@login_required
def calendar(request):

    today = timezone.now().date()

    month = int(request.GET.get("month", today.month))
    year = int(request.GET.get("year", today.year))

    pycalendar.setfirstweekday(pycalendar.SUNDAY)
    cal = pycalendar.monthcalendar(year, month)

    tickets = Ticket.objects.select_related(
        "customer", "status", "job_type",
    ).filter(
        due_date__year=year,
        due_date__month=month,
    )

    tickets_by_day = {}
    tickets_json = {}

    for ticket in tickets:
        day = ticket.due_date.day
        tickets_by_day.setdefault(day, []).append(ticket)

        latest_note = ticket.notes.order_by("-created_at").first()

        tickets_json.setdefault(day, []).append({
            "id": ticket.id,
            "ticket_number": ticket.ticket_number,
            "customer": ticket.customer.name,
            "job_type": ticket.job_type.type,
            "status": ticket.status.status,
            "color": ticket.status.color,
            "is_starred": ticket.is_starred,
            "latest_note": (
                latest_note.content
                if ticket.is_starred and latest_note
                else ""
            ),
        })

    if month == 1:
        prev_month, prev_year = 12, year - 1
    else:
        prev_month, prev_year = month - 1, year

    if month == 12:
        next_month, next_year = 1, year + 1
    else:
        next_month, next_year = month + 1, year

    months = [
        "January", "February", "March", "April",
        "May", "June", "July", "August",
        "September", "October", "November", "December"
    ]

    context = {
        "calendar_weeks": cal,
        "tickets_by_day": tickets_by_day,
        "tickets_json": json.dumps(tickets_json),
        "month": month,
        "year": year,
        "month_name": months[month - 1],
        "months": months,
        "years": range(today.year - 5, today.year + 6),
        "prev_month": prev_month,
        "prev_year": prev_year,
        "next_month": next_month,
        "next_year": next_year,
        "today": today.day,
        "today_month": today.month,
        "today_year": today.year,
        "is_current_month": (month == today.month and year == today.year),
    }

    return render(request, "core/calendar.html", context)

@login_required
def ticket_detail(request, ticket_id):

    ticket = get_object_or_404(Ticket, id=ticket_id)

    latest_note = ticket.notes.order_by("-created_at").first()

    # =========================================
    # Previous / Next Ticket Navigation
    # Ordered by ticket number
    # =========================================

    ordered_tickets = list(
        Ticket.objects
        .annotate(
            ticket_prefix=Substr("ticket_number", 1, 2),
            ticket_year=Cast(
                Substr("ticket_number", 4, 4),
                IntegerField()
            ),
            ticket_sequence=Cast(
                Substr("ticket_number", 9),
                IntegerField()
            ),
        )
        .order_by(
            "ticket_prefix",
            "ticket_year",
            "ticket_sequence"
        )
        .values_list("id", "ticket_number")
    )

    current_index = next(
        (
            index
            for index, (ticket_id_value, ticket_number) 
            in enumerate(ordered_tickets)
            if ticket_id_value == ticket.id
        ),
        None
    )

    previous_ticket = None
    next_ticket = None

    if current_index is not None:

        # Previous ticket
        if current_index > 0:
            previous_id, previous_number = ordered_tickets[current_index - 1]

            previous_ticket = {
                "id": previous_id,
                "ticket_number": previous_number,
            }

        # Next ticket
        if current_index < len(ordered_tickets) - 1:
            next_id, next_number = ordered_tickets[current_index + 1]

            next_ticket = {
                "id": next_id,
                "ticket_number": next_number,
            }

    context = {
        "ticket": ticket,

        "statuses": Status.objects.all(),

        "ready_status": Status.objects.filter(
            status="Ready for Pickup"
        ).first(),

        "completed_status": Status.objects.filter(
            status="Completed"
        ).first(),

        "latest_note": latest_note,

        # Navigation
        "previous_ticket": previous_ticket,
        "next_ticket": next_ticket,
        "ticket_position": (
            current_index + 1
            if current_index is not None
            else 0
        ),
        "ticket_total": len(ordered_tickets),
    }

    return render(
        request,
        "core/ticket_detail.html",
        context
    )
@login_required
def toggle_ticket_star(request, ticket_id):

    ticket = get_object_or_404(
        Ticket,
        id=ticket_id
    )

    if request.method == "POST":

        ticket.is_starred = not ticket.is_starred

        ticket.save(
            update_fields=["is_starred"]
        )

    return redirect(
        "ticket_detail",
        ticket_id=ticket.id
    )

@login_required
def customers(request):

    # --------------------------------
    # Customer search
    # --------------------------------
    keyword = request.GET.get("q", "").strip()

    customers_queryset = Customer.objects.annotate(
        job_count=Count("tickets")
    )

    if keyword:

        phone_digits = "".join(
            character
            for character in keyword
            if character.isdigit()
        )

        from django.db.models import Value
        from django.db.models.functions import Replace

        normalized_phone = Replace(
            Replace(
                Replace(
                    Replace(
                        "phone",
                        Value(" "),
                        Value("")
                    ),
                    Value("("),
                    Value("")
                ),
                Value(")"),
                Value("")
            ),
            Value("-"),
            Value("")
        )

        search_conditions = (
            Q(name__icontains=keyword) |
            Q(email__icontains=keyword) |
            Q(tickets__ticket_number__icontains=keyword)
        )

        if phone_digits:
            search_conditions |= Q(
                normalized_phone__icontains=phone_digits
            )

        customers_queryset = customers_queryset.annotate(
            normalized_phone=normalized_phone
        ).filter(
            search_conditions
        ).distinct()

    customers_queryset = customers_queryset.order_by("name")

    # --------------------------------
    # Customer pagination
    # --------------------------------
    paginator = Paginator(customers_queryset, 10)

    page_number = request.GET.get("page")

    customers = paginator.get_page(page_number)

    # --------------------------------
    # Selected customer
    # --------------------------------
    customer_id = request.GET.get("customer")

    if customer_id:
        customer = Customer.objects.get(id=customer_id)
    else:
        # Select the first customer on the current page
        customer = customers.object_list.first()

    # All job types
    job_types = JobType.objects.all().order_by("type")

    # Selected tab
    selected_type = request.GET.get("type", "all")

    tickets = Ticket.objects.filter(
        customer=customer
    ).select_related(
        "status",
        "job_type"
    )

    # Filter by JobType id
    if selected_type != "all":
        tickets = tickets.filter(job_type_id=selected_type)

        tickets = tickets.order_by("-created_date")

    # --------------------------------
    # Job statistics BEFORE pagination
    # --------------------------------

    total_value = tickets.aggregate(
        Sum("price")
    )["price__sum"] or 0

    # This is the number of jobs matching
    # the currently selected job type
    job_count = tickets.count()

    # Count for "All Jobs"
    all_count = Ticket.objects.filter(
        customer=customer
    ).count()

    # Add a count to every job type
    for job_type in job_types:
        job_type.ticket_count = Ticket.objects.filter(
            customer=customer,
            job_type=job_type
        ).count()

    # --------------------------------
    # Job pagination
    # --------------------------------

    job_paginator = Paginator(tickets, 10)

    job_page_number = request.GET.get("job_page")

    tickets = job_paginator.get_page(job_page_number)

    show_form = request.GET.get("new")

    context = {
        "customers": customers,
        "customer": customer,
        "tickets": tickets,

        # Job information
        "job_count": job_count,
        "total_value": total_value,

        "job_types": job_types,
        "selected_type": selected_type,
        "all_count": all_count,

        # Job pagination
        "job_paginator": job_paginator,
        "job_page": tickets,

        "show_form": show_form,
        "customer_form": CustomerForm(),
        "search_keyword": keyword,
    }

    return render(request, "core/customers.html", context)

@login_required
def edit_ticket(request, ticket_id):

    ticket = get_object_or_404(Ticket, id=ticket_id)

    if request.method == 'POST':

        old_ticket_number = ticket.ticket_number
        old_customer = ticket.customer
        old_description = ticket.description
        old_due_date = ticket.due_date
        old_price = ticket.price
        old_job_type = ticket.job_type
        old_status = ticket.status
        old_ring_finger = ticket.ring_finger

        # -------------------------
        # Ticket number
        # -------------------------

        ticket_number = request.POST.get(
            "ticket_number",
            ""
        ).strip()

        if Ticket.objects.filter(
            ticket_number__iexact=ticket_number
        ).exclude(id=ticket.id).exists():

            messages.error(
                request,
                "Ticket number already exists."
            )

            return render(
                request,
                "core/edit_ticket.html",
                {
                    "ticket": ticket,
                    "job_types": JobType.objects.all(),
                    "statuses": Status.objects.all(),
                }
            )

        ticket.ticket_number = ticket_number


        # -------------------------
        # Customer
        # -------------------------

        existing_customer_id = request.POST.get(
            "existing_customer_id",
            ""
        ).strip()

        customer_name = request.POST.get(
            "customer_name",
            ""
        ).strip()

        phone = request.POST.get(
            "phone",
            ""
        ).strip()

        email = request.POST.get(
            "email",
            ""
        ).strip()


        if existing_customer_id:

            # User selected an existing customer

            ticket.customer = get_object_or_404(
                Customer,
                pk=existing_customer_id
            )

        else:

            # Search customer by phone number

            customer = Customer.objects.filter(
                phone=phone
            ).first()


            if customer:

                # Customer exists,
                # link this ticket to that customer

                ticket.customer = customer

            else:

                # Customer does not exist,
                # create a new one

                customer = Customer.objects.create(
                    name=customer_name,
                    phone=phone,
                    email=email,
                )

                create_audit_log(
                    request,
                    "CREATE",
                    "Customer",
                    customer.id,
                    f"Created customer {customer.name} ({customer.phone})."
                )

                ticket.customer = customer


        # -------------------------
        # Other fields
        # -------------------------

        ticket.description = request.POST.get(
            "description",
            ticket.description
        )

        ticket.due_date = request.POST.get(
            "due_date",
            ticket.due_date
        )

        ticket.price = request.POST.get(
            "price"
        ) or None

        ticket.job_type_id = request.POST.get(
            "job_type",
            ticket.job_type_id
        )


        # -------------------------
        # Ring Finger
        # -------------------------

        ticket.ring_finger = request.POST.get(
            "ring_finger"
        ) or None


        # -------------------------
        # Status
        # -------------------------

        new_status_id = request.POST.get(
            "status"
        )


        if new_status_id and int(new_status_id) != ticket.status_id:

            ticket.status_id = new_status_id

            ticket.save()


            StatusHistory.objects.create(
                ticket=ticket,
                status=ticket.status,
                note="Status updated during edit."
            )

        else:

            ticket.save()


        # ===========================
        # Delete marked photos
        # ===========================

        deleted = request.POST.get(
            "deleted_photo_ids",
            ""
        )


        if deleted:

            ids = [
                int(x)
                for x in deleted.split(",")
                if x
            ]


            photos_to_delete = TicketPhoto.objects.filter(
                ticket=ticket,
                id__in=ids
            )


            for photo in photos_to_delete:

                photo_id = photo.id

                photo.delete()


                create_audit_log(
                    request,
                    "DELETE",
                    "TicketPhoto",
                    photo_id,
                    f"Deleted photo from ticket {ticket.ticket_number}."
                )


        # ===========================
        # Save new photos
        # ===========================

        for image in request.FILES.getlist("photos"):

            ticket_photo = TicketPhoto.objects.create(
                ticket=ticket,
                image=image
            )


            create_audit_log(
                request,
                "CREATE",
                "TicketPhoto",
                ticket_photo.id,
                f"Added photo to ticket {ticket.ticket_number}."
            )


        # ===========================
        # Audit changes
        # ===========================

        changes = []


        if old_ticket_number != ticket.ticket_number:

            changes.append(
                f"Ticket number: "
                f"{old_ticket_number} -> "
                f"{ticket.ticket_number}"
            )


        if old_customer != ticket.customer:

            changes.append(
                f"Customer: "
                f"{old_customer.name} -> "
                f"{ticket.customer.name}"
            )


        if old_description != ticket.description:

            changes.append(
                "Description changed"
            )


        if old_due_date != ticket.due_date:

            changes.append(
                f"Due date: "
                f"{old_due_date} -> "
                f"{ticket.due_date}"
            )


        if old_price != ticket.price:

            changes.append(
                f"Price: "
                f"{old_price} -> "
                f"{ticket.price}"
            )


        if old_job_type != ticket.job_type:

            changes.append(
                f"Job type: "
                f"{old_job_type.type} -> "
                f"{ticket.job_type.type}"
            )


        if old_status != ticket.status:

            changes.append(
                f"Status: "
                f"{old_status.status} -> "
                f"{ticket.status.status}"
            )


        # -------------------------
        # Ring finger audit
        # -------------------------

        if old_ring_finger != ticket.ring_finger:

            old_finger_display = (
                dict(Ticket.RING_FINGER_CHOICES).get(
                    old_ring_finger,
                    "None"
                )
            )

            new_finger_display = (
                dict(Ticket.RING_FINGER_CHOICES).get(
                    ticket.ring_finger,
                    "None"
                )
            )

            changes.append(
                f"Ring finger: "
                f"{old_finger_display} -> "
                f"{new_finger_display}"
            )


        # -------------------------
        # Create audit log
        # -------------------------

        if changes:

            create_audit_log(
                request,
                "UPDATE",
                "Ticket",
                ticket.ticket_number,
                "; ".join(changes)
            )


        # -------------------------
        # Redirect
        # -------------------------

        return redirect(
            'ticket_detail',
            ticket_id=ticket.id
        )


    # ===========================
    # GET request
    # ===========================

    return render(
        request,
        'core/edit_ticket.html',
        {
            'ticket': ticket,
            'job_types': JobType.objects.all(),
            'statuses': Status.objects.all(),
        }
    )
@login_required
def add_note(request, ticket_id):

    ticket = get_object_or_404(Ticket, id=ticket_id)

    if request.method == 'POST':
        content = request.POST.get('content', '').strip()
        if content:
            note = Note.objects.create(ticket=ticket, content=content)
            create_audit_log(
                request,
                "CREATE",
                "Note",
                note.id,
                f"Created note for ticket {ticket.ticket_number}."
            )

    next_path = request.POST.get('next')
    if next_path:
        return redirect(next_path)
    return redirect('ticket_detail', ticket_id=ticket.id)

@login_required
@login_required
def add_photo(request, ticket_id):

    ticket = get_object_or_404(Ticket, id=ticket_id)

    if request.method == "POST":

        # ========================================
        # 1. Delete photos marked for deletion
        # ========================================

        deleted_photo_ids = request.POST.get(
            "deleted_photo_ids",
            ""
        )

        if deleted_photo_ids:

            photo_ids = [
                int(photo_id)
                for photo_id in deleted_photo_ids.split(",")
                if photo_id.isdigit()
            ]

            photos_to_delete = ticket.photos.filter(
                id__in=photo_ids
            )

            for photo in photos_to_delete:

                # Delete actual image file
                if photo.image:
                    photo.image.delete(save=False)

                # Delete database record
                photo.delete()


        # ========================================
        # 2. Add new photos
        # ========================================

        for uploaded_file in request.FILES.getlist("photos"):

            TicketPhoto.objects.create(
                ticket=ticket,
                image=uploaded_file
            )


        # ========================================
        # 3. Return to the page we came from
        # ========================================

        next_url = request.POST.get("next")

        if next_url:
            return redirect(next_url)

        return redirect("ticket_detail", ticket.id)


    return redirect("ticket_detail", ticket.id)

@login_required
def set_status(request, ticket_id, status_id):

    ticket = get_object_or_404(Ticket, id=ticket_id)
    status = get_object_or_404(Status, id=status_id)

    old_status = ticket.status.status

    ticket.status = status

    # 如果状态是 Completed，则记录完成日期
    if status.status.lower() == "completed":
        ticket.completed_date = timezone.localdate()
    else:
        # 如果改成其他状态，则清空完成日期
        if ticket.completed_date is not None:
            ticket.completed_date = None

    ticket.save()

    create_audit_log(
    request,
    "UPDATE",
    "Ticket",
    ticket.ticket_number,
    f"Changed status of ticket {ticket.ticket_number}: "
    f"{old_status} -> {status.status}"
)

    StatusHistory.objects.create(
        ticket=ticket,
        status=status,
        note=""
    )

    return redirect('ticket_detail', ticket_id=ticket.id)

@login_required
def delete_note(request, note_id):
    note = get_object_or_404(Note, id=note_id)

    ticket_id = note.ticket.id
    ticket_number = note.ticket.ticket_number
    note_id = note.id
    note.delete()
    create_audit_log(
        request,
        "DELETE",
        "Note",
        note_id,
        f"Deleted note from ticket {ticket_number}."
    )

    return redirect("ticket_detail", ticket_id)

@login_required
def base(request):
    return render(request, 'core/base.html')

def test_error(request):
    raise Exception("TEST ERROR - Jewelry System")

@login_required
def all_molds(request):

    # -----------------------------------------
    # Get all molds
    # -----------------------------------------

    molds_queryset = Mold.objects.select_related(
        "type"
    ).prefetch_related(
        "tags"
    ).order_by(
        "mold_code"
    )

    # -----------------------------------------
    # Search
    # -----------------------------------------

    keyword = request.GET.get("q", "").strip()

    if keyword:
        molds_queryset = molds_queryset.filter(
            Q(mold_code__icontains=keyword)
            | Q(file_name__icontains=keyword)
            | Q(type__name__icontains=keyword)
            | Q(tags__name__icontains=keyword)
        ).distinct()

    # -----------------------------------------
    # Type filter
    # -----------------------------------------

    selected_type = request.GET.get(
        "type",
        "all",
    )

    if selected_type and selected_type != "all" and selected_type != "like":
        molds_queryset = molds_queryset.filter(
            type_id=selected_type
        )
    elif selected_type == "like":
        molds_queryset = molds_queryset.filter(
            is_liked=True
        )

    # -----------------------------------------
    # Tag filter
    # -----------------------------------------

    selected_tags = request.GET.getlist(
        "tag"
    )

    if selected_tags:
        tag_query = Q()

        for tag_id in selected_tags:
            tag_query |= Q(
                tags__id=tag_id
            )

        molds_queryset = molds_queryset.filter(
            tag_query
        ).distinct()

    # -----------------------------------------
    # Liked filter
    # -----------------------------------------

    liked = request.GET.get(
        "liked",
        ""
    )

    if liked == "1":
        molds_queryset = molds_queryset.filter(
            is_liked=True
        )

    # -----------------------------------------
    # Get filter data
    # -----------------------------------------

    mold_types = MoldType.objects.all().order_by(
        "name"
    )

    mold_tags = MoldTag.objects.all().order_by(
        "name"
    )

    # -----------------------------------------
    # Pagination
    # -----------------------------------------

    paginator = Paginator(
        molds_queryset,
        15
    )

    page_number = request.GET.get(
        "page"
    )

    molds = paginator.get_page(
        page_number
    )

    # -----------------------------------------
    # Context
    # -----------------------------------------

    context = {
        "molds": molds,
        "mold_count": molds.paginator.count,

        "mold_types": mold_types,
        "mold_tags": mold_tags,

        "keyword": keyword,
        "selected_type": selected_type,
        "selected_tags": selected_tags,
        "liked": liked,
    }

    return render(
        request,
        "core/all_molds.html",
        context
    )


@login_required
def mold_toggle_like(request):

    if request.method != "POST":
        return JsonResponse(
            {"success": False},
            status=405
        )

    mold_id = request.POST.get(
        "mold_id"
    )

    mold = get_object_or_404(
        Mold,
        id=mold_id
    )

    mold.is_liked = not mold.is_liked

    mold.save(
        update_fields=["is_liked"]
    )

    return JsonResponse({
        "success": True,
        "is_liked": mold.is_liked
    })


@login_required
def mold_detail(request, pk):

    mold = get_object_or_404(
        Mold.objects.prefetch_related("tags"),
        pk=pk
    )

    # =========================================================
    # EDIT MODE
    # =========================================================

    edit_mode = request.GET.get("edit") == "1"


    # =========================================================
    # SAVE CHANGES
    # =========================================================

    if request.method == "POST":

        # -----------------------------------------------------
        # Mold Code
        # -----------------------------------------------------

        mold_code = request.POST.get(
            "mold_code",
            ""
        ).strip()


        # Check required field
        if not mold_code:

            messages.error(
                request,
                "Mold code is required."
            )

            return render(
                request,
                "core/mold_detail.html",
                {
                    "mold": mold,
                    "edit_mode": True,
                    "mold_types": MoldType.objects.all().order_by("name"),
                    "mold_tags": MoldTag.objects.all().order_by("name"),
                }
            )


        # Check duplicate mold code
        if Mold.objects.filter(
            mold_code__iexact=mold_code
        ).exclude(
            pk=mold.pk
        ).exists():

            messages.error(
                request,
                "Mold code already exists."
            )

            return render(
                request,
                "core/mold_detail.html",
                {
                    "mold": mold,
                    "edit_mode": True,
                    "mold_types": MoldType.objects.all().order_by("name"),
                    "mold_tags": MoldTag.objects.all().order_by("name"),
                }
            )


        # -----------------------------------------------------
        # Mold Type
        # -----------------------------------------------------

        type_id = request.POST.get("type")

        if not type_id:

            messages.error(
                request,
                "Please select a mold type."
            )

            return render(
                request,
                "core/mold_detail.html",
                {
                    "mold": mold,
                    "edit_mode": True,
                    "mold_types": MoldType.objects.all().order_by("name"),
                    "mold_tags": MoldTag.objects.all().order_by("name"),
                }
            )


        mold_type = get_object_or_404(
            MoldType,
            pk=type_id
        )


        # -----------------------------------------------------
        # File Name
        # -----------------------------------------------------

        file_name = request.POST.get(
            "file_name",
            ""
        ).strip()


        if not file_name:

            messages.error(
                request,
                "File name is required."
            )

            return render(
                request,
                "core/mold_detail.html",
                {
                    "mold": mold,
                    "edit_mode": True,
                    "mold_types": MoldType.objects.all().order_by("name"),
                    "mold_tags": MoldTag.objects.all().order_by("name"),
                }
            )


        # -----------------------------------------------------
        # Description
        # -----------------------------------------------------

        description = request.POST.get(
            "description",
            ""
        ).strip()


        # -----------------------------------------------------
        # Save basic information
        # -----------------------------------------------------

        old_mold_code = mold.mold_code
        old_file_name = mold.file_name
        old_type = mold.type
        old_description = mold.description
        old_is_liked = mold.is_liked


        mold.mold_code = mold_code
        mold.file_name = file_name
        mold.type = mold_type
        mold.description = description


        # -----------------------------------------------------
        # Like / Unlike
        # -----------------------------------------------------

        mold.is_liked = (
            request.POST.get("is_liked") == "on"
        )


        # -----------------------------------------------------
        # Preview Image
        # -----------------------------------------------------

        # -----------------------------------------------------
        # Preview Image
        # -----------------------------------------------------

        remove_preview_image = (
            request.POST.get("remove_preview_image")
            == "1"
        )


        if remove_preview_image:

            # Delete the old physical image file
            if mold.preview_image:

                mold.preview_image.delete(
                    save=False
                )

            mold.preview_image = None


        elif "preview_image" in request.FILES:

            # Replace with new image
            mold.preview_image = request.FILES[
                "preview_image"
            ]


        # -----------------------------------------------------
        # Save Mold
        # -----------------------------------------------------

        mold.save()


        # =====================================================
        # TAGS
        # =====================================================

        tag_ids = request.POST.getlist("tags")


        # Only use valid integer IDs
        valid_tag_ids = []

        for tag_id in tag_ids:

            try:

                valid_tag_ids.append(
                    int(tag_id)
                )

            except (TypeError, ValueError):

                continue


        # Make sure all IDs actually exist
        tags = MoldTag.objects.filter(
            id__in=valid_tag_ids
        )


        mold.tags.set(tags)


        # =====================================================
        # AUDIT LOG
        # =====================================================

        changes = []


        if old_mold_code != mold.mold_code:

            changes.append(
                f"Mold code: "
                f"{old_mold_code} -> "
                f"{mold.mold_code}"
            )


        if old_file_name != mold.file_name:

            changes.append(
                f"File name: "
                f"{old_file_name} -> "
                f"{mold.file_name}"
            )


        if old_type != mold.type:

            changes.append(
                f"Type: "
                f"{old_type.name} -> "
                f"{mold.type.name}"
            )


        if old_description != mold.description:

            changes.append(
                "Description changed"
            )


        if old_is_liked != mold.is_liked:

            if mold.is_liked:

                changes.append(
                    "Mold liked"
                )

            else:

                changes.append(
                    "Mold unliked"
                )


        # Image changed
        if "preview_image" in request.FILES:

            changes.append(
                "Preview image changed"
            )


        if changes:

            create_audit_log(
                request,
                "UPDATE",
                "Mold",
                mold.id,
                "; ".join(changes)
            )


        # =====================================================
        # SUCCESS
        # =====================================================

        messages.success(
            request,
            "Mold updated successfully."
        )


        return redirect(
            "mold_detail",
            pk=mold.pk
        )


    # =========================================================
    # GET / DISPLAY PAGE
    # =========================================================

    context = {

        "mold": mold,

        "edit_mode": edit_mode,

        # Used by the mold type dropdown
        "mold_types": MoldType.objects.all().order_by(
            "name"
        ),

        # Used by the tags section
        "mold_tags": MoldTag.objects.all().order_by(
            "name"
        ),
    }


    return render(
        request,
        "core/mold_detail.html",
        context
    )


@login_required
def create_mold_tag(request):

    if request.method != "POST":

        return JsonResponse(
            {
                "success": False,
                "error": "POST request required."
            },
            status=405
        )


    name = request.POST.get(
        "name",
        ""
    ).strip()


    if not name:

        return JsonResponse(
            {
                "success": False,
                "error": "Tag name is required."
            },
            status=400
        )


    # ---------------------------------------------------------
    # Check if tag already exists
    # ---------------------------------------------------------

    existing_tag = MoldTag.objects.filter(
        name__iexact=name
    ).first()


    if existing_tag:

        return JsonResponse(
            {
                "success": True,
                "id": existing_tag.id,
                "name": existing_tag.name,
                "created": False,
            }
        )


    # ---------------------------------------------------------
    # Create new tag
    # ---------------------------------------------------------

    tag = MoldTag.objects.create(
        name=name
    )


    return JsonResponse(
        {
            "success": True,
            "id": tag.id,
            "name": tag.name,
            "created": True,
        }
    )
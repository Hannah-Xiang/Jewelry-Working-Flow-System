from datetime import date, timedelta
from django.db.models import Max
from .models import Ticket, JobType
from .models import Customer


def generate_ticket_number():
    """
    Generate a unique ticket number.

    Format:
        ZJ-2026-0001
        ZJ-2026-0002
        ZJ-2027-0001
    """

    year = date.today().year
    prefix = f"ZJ-{year}-"

    last_ticket = (
        Ticket.objects
        .filter(ticket_number__startswith=prefix)
        .order_by("-ticket_number")
        .first()
    )

    if last_ticket:
        last_number = int(last_ticket.ticket_number.split("-")[-1])
        next_number = last_number + 1
    else:
        next_number = 1

    return f"{prefix}{next_number:04d}"


def calculate_due_date(job_type):
    """
    Calculate the default due date
    based on JobType.duration.
    """

    if isinstance(job_type, JobType):
        duration = job_type.duration
    else:
        duration = JobType.objects.get(pk=job_type).duration

    return date.today() + timedelta(days=duration)





def get_or_create_customer(name, phone, email=""):
    """
    Find customer by name + phone (case-insensitive).
    If not exists, create one.
    """

    customer = Customer.objects.filter(
        phone__iexact=phone.strip()
    ).first()

    if customer:
        return customer

    return Customer.objects.create(
        name=name.strip(),
        phone=phone.strip(),
        email=email.strip()
    )
from datetime import date, timedelta
from django.db.models import Max
from django.apps import apps


from datetime import date
from django.apps import apps


def generate_ticket_number():
    Ticket = apps.get_model("core", "Ticket")

    year = date.today().year
    prefix = f"ZJ-{year}-"

    # 获取最后创建的一张工单（按数据库ID）
    last_ticket = (
        Ticket.objects
        .order_by("-id")
        .first()
    )

    if last_ticket:
        try:
            last_number = int(last_ticket.ticket_number.split("-")[-1])
        except (ValueError, IndexError):
            last_number = 0
    else:
        last_number = 0

    next_number = last_number

    while True:
        # 加一，并循环回0001
        next_number += 1
        if next_number > 9999:
            next_number = 1

        ticket_number = f"{prefix}{next_number:04d}"

        # 当前年份不存在即可使用
        if not Ticket.objects.filter(ticket_number=ticket_number).exists():
            return ticket_number


def calculate_due_date(job_type):

    JobType = apps.get_model("core", "JobType")

    if isinstance(job_type, JobType):
        duration = job_type.duration
    else:
        duration = JobType.objects.get(pk=job_type).duration

    return date.today() + timedelta(days=duration)


def get_or_create_customer(name, phone, email="", wedding_date=None):

    Customer = apps.get_model("core", "Customer")

    customer = Customer.objects.filter(
        phone__iexact=phone.strip()
    ).first()

    if customer:
        return customer

    return Customer.objects.create(
        name=name.strip(),
        phone=phone.strip(),
        email=email.strip(),
        wedding_date=wedding_date
    )

# =========================================================
# Ticket <-> Diamond status sync
# =========================================================

def ticket_is_completed(ticket):
    return bool(
        ticket.status_id
        and ticket.status.status.lower() == "completed"
    )


def sync_ticket_diamonds(ticket, added=(), removed=()):
    """
    Keep diamond status in line with the tickets that use it.

    added   -> available/used becomes reserved (or sold if the
               ticket is already completed)
    removed -> reserved/sold goes back to the status it had
               before it was reserved, unless another ticket
               still uses it
    Always  -> diamonds on a completed ticket are sold; diamonds
               on any other ticket that are sold go back to reserved

    Returns a list of human-readable change strings for the audit log.
    """

    changes = []
    completed = ticket_is_completed(ticket)

    def set_status(diamond, new_status, clear_previous=False):
        old_status = diamond.status
        if old_status == new_status and not clear_previous:
            return
        diamond.status = new_status
        fields = ["status", "updated_at"]
        if clear_previous:
            diamond.status_before_reserve = ""
            fields.append("status_before_reserve")
        diamond.save(update_fields=fields)
        if old_status != new_status:
            changes.append(
                f"Diamond {diamond.report_number or diamond.pk}: "
                f"{old_status} -> {new_status}"
            )

    # ---- Newly linked diamonds ----
    for diamond in added:
        if diamond.status in ("available", "used"):
            diamond.status_before_reserve = diamond.status
            diamond.save(update_fields=["status_before_reserve"])
            set_status(diamond, "sold" if completed else "reserved")

    # ---- Unlinked diamonds ----
    for diamond in removed:
        still_used = diamond.related_tickets.exclude(
            pk=ticket.pk
        ).exists()

        if still_used:
            continue

        if diamond.status in ("reserved", "sold"):
            set_status(
                diamond,
                diamond.status_before_reserve or "available",
                clear_previous=True
            )

    # ---- Status pass for all diamonds still linked ----
    if ticket.pk:
        removed_ids = {d.pk for d in removed}
        for diamond in ticket.diamonds.all():
            if diamond.pk in removed_ids:
                continue
            if completed and diamond.status == "reserved":
                set_status(diamond, "sold")
            elif not completed and diamond.status == "sold":
                set_status(diamond, "reserved")

    return changes


from PIL import Image, ImageOps
from pathlib import Path


def compress_image(image_path):

    image_path = Path(image_path)

    if not image_path.exists():
        return

    img = Image.open(image_path)

    # 自动修正手机拍照方向
    img = ImageOps.exif_transpose(img)

    # 转 RGB
    if img.mode != "RGB":
        img = img.convert("RGB")

    # 最大边
    MAX_SIZE = 1600

    img.thumbnail((MAX_SIZE, MAX_SIZE))

    img.save(
        image_path,
        "JPEG",
        quality=85,
        optimize=True
    )
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


def get_or_create_customer(name, phone, email=""):

    Customer = apps.get_model("core", "Customer")

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
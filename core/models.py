from django.db import models

class Customer(models.Model):
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True, null=True)
    note = models.TextField(blank=True)

    created_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.phone})"


class JobType(models.Model):
    type = models.CharField(max_length=100, unique=True)

    # 默认完成天数
    duration = models.PositiveIntegerField(default=7)

    def __str__(self):
        return self.type


class Status(models.Model):
    status = models.CharField(max_length=50, unique=True)

    # Dashboard颜色
    color = models.CharField(max_length=20, default="#c79c3d")

    def __str__(self):
        return self.status


class Ticket(models.Model):

    ticket_number = models.CharField(
        max_length=20,
        unique=True
    )

    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="tickets"
    )

    job_type = models.ForeignKey(
        JobType,
        on_delete=models.PROTECT
    )

    status = models.ForeignKey(
        Status,
        on_delete=models.PROTECT
    )

    description = models.TextField()

    created_date = models.DateTimeField(auto_now_add=True)

    due_date = models.DateField()

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True
    )

    completed_date = models.DateField(
        blank=True,
        null=True
    )

    def __str__(self):
        return self.ticket_number


class TicketPhoto(models.Model):

    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name="photos"
    )

    image = models.ImageField(
        upload_to="tickets/"
    )

    uploaded_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.ticket.ticket_number

class Note(models.Model):
    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name="notes"
    )

    content = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Note for {self.ticket.ticket_number}"
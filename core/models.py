from django.db import models

# Create your models here.
# core/models.py

from django.db import models


class Customer(models.Model):
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True, null=True)
    note = models.TextField(blank=True)

    def __str__(self):
        return self.name


class JobType(models.Model):
    type = models.CharField(max_length=100)
    duration = models.PositiveIntegerField()

    def __str__(self):
        return self.type


class Status(models.Model):
    status = models.CharField(max_length=50)
    color = models.CharField(max_length=20)

    def __str__(self):
        return self.status


class Ticket(models.Model):
    ticket_number = models.CharField(max_length=20, unique=True)

    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="tickets"
    )

    job_type = models.ForeignKey(
        JobType,
        on_delete=models.PROTECT
    )

    description = models.TextField()

    status = models.ForeignKey(
        Status,
        on_delete=models.PROTECT
    )

    created_date = models.DateField(auto_now_add=True)

    due_date = models.DateField()

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )

    def __str__(self):
        return f"{self.ticket_number} - {self.customer.name}"
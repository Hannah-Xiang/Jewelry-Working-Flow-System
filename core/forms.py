from django import forms
from .models import Ticket


class TicketForm(forms.ModelForm):

    # Customer Information
    customer_name = forms.CharField(
        max_length=100,
        required=True,
        label="Customer Name"
    )

    phone = forms.CharField(
        max_length=20,
        required=True,
        label="Phone Number"
    )

    email = forms.EmailField(
        required=False,
        label="Email Address"
    )

    class Meta:

        model = Ticket

        fields = [
            "ticket_number",
            "job_type",
            "description",
            "status",
            "due_date",
        ]

        widgets = {

            "ticket_number": forms.TextInput(
                attrs={
                    "class": "form-control"
                }
            ),

            "job_type": forms.Select(
                attrs={
                    "class": "form-control"
                }
            ),

            "description": forms.Textarea(
                attrs={
                    "rows": 5,
                    "class": "form-control",
                    "placeholder": "Describe the work in detail..."
                }
            ),

            "status": forms.Select(
                attrs={
                    "class": "form-control"
                }
            ),

            "due_date": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "form-control"
                }
            )

        }

    # -----------------------------
    # Validation
    # -----------------------------

    def clean_ticket_number(self):

        ticket_number = self.cleaned_data["ticket_number"].strip()

        if Ticket.objects.filter(
            ticket_number__iexact=ticket_number
        ).exists():

            raise forms.ValidationError(
                "Ticket Number already exists."
            )

        return ticket_number

    def clean_customer_name(self):

        return self.cleaned_data["customer_name"].strip()

    def clean_phone(self):

        return self.cleaned_data["phone"].strip()

    def clean_email(self):

        email = self.cleaned_data.get("email")

        if email:
            return email.strip().lower()

        return ""
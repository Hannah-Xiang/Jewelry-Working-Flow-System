from encodings.punycode import digits
import re
from unicodedata import name

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

        name = self.cleaned_data["customer_name"].strip()

        # Remove extra spaces between words
        name = " ".join(name.split())

        # Capitalize the first letter of each word
        name = name.title()

        return name

    def clean_phone(self):

        return self.cleaned_data["phone"].strip()

    def clean_email(self):

        email = self.cleaned_data.get("email")

        if email:
            return email.strip().lower()

        return ""
    

from .models import Customer

import re
from django import forms
from .models import Customer


class CustomerForm(forms.ModelForm):

    class Meta:
        model = Customer

        fields = [
            "name",
            "phone",
            "email",
            "note",
        ]

        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "First and last name",
                }
            ),

            "phone": forms.TextInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "(519) 555-0000",
                }
            ),

            "email": forms.EmailInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "customer@email.com",
                }
            ),

            "note": forms.Textarea(
                attrs={
                    "class": "form-input",
                    "rows": 5,
                    "placeholder": "Preferences, allergies, special notes...",
                }
            ),
        }
    
    def clean_name(self):

        name = self.cleaned_data["name"].strip()

        # Remove extra spaces between words
        name = " ".join(name.split())

        # Capitalize the first letter of each word
        name = name.title()

        return name

    def clean_phone(self):

        phone = self.cleaned_data["phone"].strip()

        # Remove everything except digits
        digits = re.sub(r"\D", "", phone)

        # Remove leading 1 (Canada/US country code)
        if len(digits) == 11 and digits.startswith("1"):
            digits = digits[1:]

        # Must be exactly 10 digits
        if len(digits) != 10:
            raise forms.ValidationError(
                "Please enter a valid Canadian phone number."
            )

        # Canadian area code and central office code cannot start with 0 or 1
        if digits[0] in "01" or digits[3] in "01":
            raise forms.ValidationError(
                "Please enter a valid Canadian phone number."
            )

        # Check duplicate phone number
        customers = Customer.objects.filter(
            phone=f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
        )

        # If editing, ignore the current customer
        if self.instance.pk:
            customers = customers.exclude(pk=self.instance.pk)

        if customers.exists():
            raise forms.ValidationError(
                "A customer with this phone number already exists."
            )

        # Store in a consistent format
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
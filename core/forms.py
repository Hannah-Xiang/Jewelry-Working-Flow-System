from encodings.punycode import digits
import re
from unicodedata import name

from django import forms
from .models import Ticket, Customer, Mold, MoldType, Diamond


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

    
    wedding_date = forms.DateField(
        required=False,
        label="Wedding Date",
        widget=forms.DateInput(
            attrs={
                "type": "date",
                "class": "form-control",
                "id": "id_wedding_date",
            }
        ),
    )


    

    class Meta:

        model = Ticket

        fields = [
            "ticket_number",
            "job_type",
            "description",
            "status",
            "due_date",
            "price",
            #finger ring
            "ring_finger",
            "is_starred",
            
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
            ),
            "price": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "placeholder": "Enter price or estimate"
                }
            ),
            "is_starred": forms.CheckboxInput(
                attrs={
                    "class": "star-checkbox"
                }
),

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

    # def clean_ticket_number(self):

    #     ticket_number = self.cleaned_data["ticket_number"].strip()

    #     tickets = Ticket.objects.filter(
    #         ticket_number__iexact=ticket_number
    #     )

    #     # Ignore the current ticket when editing
    #     if self.instance.pk:
    #         tickets = tickets.exclude(pk=self.instance.pk)

    #     if tickets.exists():
    #         raise forms.ValidationError(
    #             "Ticket Number already exists."
    #         )

    #     return ticket_number

    def clean_customer_name(self):

        name = self.cleaned_data["customer_name"].strip()

        # Remove extra spaces between words
        name = " ".join(name.split())

        # Capitalize the first letter of each word
        name = name.title()

        return name

    def clean_phone(self):

        phone = self.cleaned_data["phone"].strip()

        # Remove everything except digits
        digits = re.sub(r"\D", "", phone)

        # Remove leading 1
        if len(digits) == 11 and digits.startswith("1"):
            digits = digits[1:]

        # Must be exactly 10 digits
        if len(digits) != 10:
            raise forms.ValidationError(
                "Please enter a valid Canadian phone number."
            )

        # Canadian numbering rules
        if digits[0] in "01" or digits[3] in "01":
            raise forms.ValidationError(
                "Please enter a valid Canadian phone number."
            )

        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"

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
            "wedding_date",
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

            "wedding_date": forms.DateInput(
                attrs={
                    "class": "form-input",
                    "type": "date",
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



from django import forms
from .models import Mold, MoldType



class MoldForm(forms.ModelForm):
    class Meta:
        model = Mold
        fields = [
            "mold_code",
            "file_name",
            "type",
            "description",
            "is_liked",
            "preview_image",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["type"].queryset = MoldType.objects.order_by("name")
        self.fields["description"].required = False
        self.fields["is_liked"].required = False
        self.fields["preview_image"].required = False

    def clean_mold_code(self):
        mold_code = self.cleaned_data["mold_code"].strip()

        # Check duplicates without considering uppercase/lowercase
        existing_molds = Mold.objects.filter(
            mold_code__iexact=mold_code
        )

        # Exclude the current record when editing, if applicable
        if self.instance.pk:
            existing_molds = existing_molds.exclude(
                pk=self.instance.pk
            )

        if existing_molds.exists():
            raise forms.ValidationError(
                "This mold code already exists. Please enter a different mold code."
            )

        return mold_code




class DiamondForm(forms.ModelForm):

    autocomplete_fields = [
        "shape",
        "color_grade",
        "clarity_grade",
        "polish",
        "symmetry",
        "fluorescence",
    ]

    class Meta:
        model = Diamond
        fields = [
            "report_number",
            "diamond_date",
            "report_link",
            "shape",
            "measurements",
            "carat_weight",
            "color_grade",
            "clarity_grade",
            "diamond_type",
            "polish",
            "symmetry",
            "fluorescence",
            "company",
            "picture",
            "status",
            "notes",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field_name in self.autocomplete_fields:

            self.fields[field_name].widget = forms.TextInput(attrs={
                "id": f"id_{field_name}",
                "autocomplete": "off",
                "placeholder": "Search or enter value...",
                "class": "new-diamond-uppercase-input",
            })

            choices = (
                Diamond.objects
                .exclude(**{f"{field_name}__isnull": True})
                .exclude(**{field_name: ""})
                .values_list(field_name, flat=True)
                .distinct()
                .order_by(field_name)
            )

            setattr(self, f"{field_name}_choices", choices)

    def clean(self):
        cleaned_data = super().clean()

        for field_name in self.autocomplete_fields:
            value = cleaned_data.get(field_name)

            if value:
                cleaned_data[field_name] = value.strip().upper()

        return cleaned_data

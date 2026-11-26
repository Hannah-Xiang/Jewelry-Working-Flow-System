from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import (
    Customer,
    Diamond,
    JobType,
    Mold,
    MoldType,
    Status,
    Ticket,
)


class TicketDiamondLinkTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user("staff", password="pw")
        self.client.login(username="staff", password="pw")

        self.job = JobType.objects.create(type="Custom")
        self.received = Status.objects.create(status="Received")
        self.in_progress = Status.objects.create(status="In Progress")
        self.completed = Status.objects.create(status="Completed")

        self.mold_type = MoldType.objects.create(name="Ring")
        self.mold1 = Mold.objects.create(
            mold_code="M001", file_name="Solitaire", type=self.mold_type
        )
        self.mold2 = Mold.objects.create(
            mold_code="M002", file_name="Halo", type=self.mold_type
        )

        self.d_avail = Diamond.objects.create(report_number="A1", status="available")
        self.d_used = Diamond.objects.create(report_number="U1", status="used")
        self.d_sold = Diamond.objects.create(report_number="S1", status="sold")

    def create_ticket(self, molds=(), diamonds=()):
        response = self.client.post(reverse("new_ticket"), {
            "ticket_number": "ZJ-2026-0001",
            "customer_name": "Jane Doe",
            "phone": "5195550000",
            "email": "",
            "job_type": self.job.id,
            "description": "Ring",
            "status": self.received.id,
            "due_date": date.today().isoformat(),
            "price": "",
            "mold_ids": [m.id for m in molds],
            "diamond_ids": [d.id for d in diamonds],
        })
        self.assertEqual(response.status_code, 302, getattr(response, "context", None) and response.context["form"].errors)
        return Ticket.objects.get(ticket_number="ZJ-2026-0001")

    def edit_ticket(self, ticket, molds=(), diamonds=(), status=None):
        return self.client.post(reverse("edit_ticket", args=[ticket.id]), {
            "ticket_number": ticket.ticket_number,
            "existing_customer_id": ticket.customer_id,
            "description": ticket.description,
            "due_date": ticket.due_date.isoformat(),
            "job_type": ticket.job_type_id,
            "status": (status or ticket.status).id,
            "mold_ids": [m.id for m in molds],
            "diamond_ids": [d.id for d in diamonds],
        })

    def refresh(self, *objs):
        for obj in objs:
            obj.refresh_from_db()

    def test_full_lifecycle(self):
        ticket = self.create_ticket(
            molds=[self.mold1, self.mold2],
            diamonds=[self.d_avail, self.d_used],
        )

        # Linked
        self.assertEqual(set(ticket.molds.all()), {self.mold1, self.mold2})
        self.assertEqual(set(ticket.diamonds.all()), {self.d_avail, self.d_used})
        self.refresh(self.d_avail, self.d_used)
        self.assertEqual(self.d_avail.status, "reserved")
        self.assertEqual(self.d_used.status, "reserved")

        # History visible on mold + diamond pages
        self.assertContains(
            self.client.get(reverse("mold_detail", args=[self.mold1.pk])),
            ticket.ticket_number,
        )
        self.assertContains(
            self.client.get(reverse("diamond_detail", args=[self.d_avail.pk])),
            ticket.ticket_number,
        )
        self.assertContains(
            self.client.get(reverse("ticket_detail", args=[ticket.pk])),
            "M002",
        )

        # Completed -> sold
        self.client.get(reverse("set_status", args=[ticket.id, self.completed.id]))
        self.refresh(self.d_avail, self.d_used)
        self.assertEqual(self.d_avail.status, "sold")
        self.assertEqual(self.d_used.status, "sold")

        # Reopened -> reserved
        self.client.get(reverse("set_status", args=[ticket.id, self.in_progress.id]))
        self.refresh(self.d_avail, self.d_used)
        self.assertEqual(self.d_avail.status, "reserved")

        # Unlink the used diamond via edit -> back to used
        ticket.refresh_from_db()
        self.edit_ticket(ticket, molds=[self.mold1], diamonds=[self.d_avail])
        self.refresh(self.d_avail, self.d_used)
        self.assertEqual(self.d_used.status, "used")
        self.assertEqual(self.d_avail.status, "reserved")
        self.assertEqual(list(ticket.molds.all()), [self.mold1])

        # Delete ticket -> back to available
        self.client.post(reverse("delete_ticket", args=[ticket.id]))
        self.refresh(self.d_avail)
        self.assertEqual(self.d_avail.status, "available")
        self.assertEqual(self.d_avail.status_before_reserve, "")

    def test_edit_to_completed_marks_sold(self):
        ticket = self.create_ticket(diamonds=[self.d_avail])
        self.edit_ticket(ticket, diamonds=[self.d_avail], status=self.completed)
        self.refresh(self.d_avail)
        self.assertEqual(self.d_avail.status, "sold")

    def test_cannot_link_sold_or_reserved_diamond(self):
        ticket = self.create_ticket(diamonds=[self.d_sold])
        self.assertEqual(ticket.diamonds.count(), 0)
        self.refresh(self.d_sold)
        self.assertEqual(self.d_sold.status, "sold")

    def test_diamond_search_filters_status(self):
        data = self.client.get(reverse("diamond_picker_search")).json()
        numbers = {d["report_number"] for d in data["results"]}
        self.assertEqual(numbers, {"A1", "U1"})

    def test_diamond_search_includes_ticket_own_diamonds(self):
        ticket = self.create_ticket(diamonds=[self.d_avail])
        data = self.client.get(
            reverse("diamond_picker_search"), {"ticket": ticket.id}
        ).json()
        numbers = {d["report_number"] for d in data["results"]}
        self.assertIn("A1", numbers)  # reserved, but on this ticket

    def test_diamond_image_fallbacks(self):
        # Picture set but the file is missing on disk -> shape image
        self.d_avail.shape = "OVAL"
        self.d_avail.picture.name = "diamonds/does-not-exist.jpg"
        self.assertFalse(self.d_avail.has_picture_file)
        self.assertTrue(self.d_avail.image_url.endswith("oval.jpg"))

        # Unknown shape, no picture -> generic icon
        self.d_used.shape = "TRILLION"
        self.assertTrue(self.d_used.image_url.endswith("default.svg"))

        # Pages render with the fallback images
        self.d_avail.save()
        self.assertContains(
            self.client.get(reverse("diamond_detail", args=[self.d_avail.pk])),
            "oval.jpg",
        )
        self.assertContains(self.client.get(reverse("all_diamonds")), "default.svg")
        ajax = self.client.get(
            reverse("all_diamonds"), HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        ).json()
        self.assertTrue(all(d["picture_url"] for d in ajax["diamonds"]))

    def test_mold_search(self):
        data = self.client.get(reverse("mold_picker_search"), {"q": "halo"}).json()
        self.assertEqual([m["mold_code"] for m in data["results"]], ["M002"])

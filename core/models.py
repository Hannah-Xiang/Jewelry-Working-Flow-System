from django.db import models
from django.core.exceptions import ValidationError
from core.utils import compress_image
import re


# =========================================================
# Customer
# =========================================================

class Customer(models.Model):
    name = models.CharField(max_length=100)

    phone = models.CharField(
        max_length=20,
        unique=True
    )

    email = models.EmailField(
        blank=True,
        null=True
    )

    note = models.TextField(
        blank=True
    )

    wedding_date = models.DateField(
        blank=True,
        null=True
    )

    created_date = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.phone})"


# =========================================================
# Job Type
# =========================================================

class JobType(models.Model):
    type = models.CharField(
        max_length=100,
        unique=True
    )

    # 默认完成天数
    duration = models.PositiveIntegerField(
        default=7
    )

    def __str__(self):
        return self.type


# =========================================================
# Status
# =========================================================

class Status(models.Model):
    status = models.CharField(
        max_length=50,
        unique=True
    )

    # Dashboard颜色
    color = models.CharField(
        max_length=20,
        default="#c79c3d"
    )

    def __str__(self):
        return self.status


# =========================================================
# Ticket
# =========================================================

class Ticket(models.Model):

    ticket_number = models.CharField(
        max_length=20,
        unique=True
    )

    RING_FINGER_CHOICES = [
        ("left_thumb", "Left Thumb"),
        ("left_index", "Left Index"),
        ("left_middle", "Left Middle"),
        ("left_ring", "Left Ring"),
        ("left_little", "Left Little"),

        ("right_thumb", "Right Thumb"),
        ("right_index", "Right Index"),
        ("right_middle", "Right Middle"),
        ("right_ring", "Right Ring"),
        ("right_little", "Right Little"),
    ]

    ring_finger = models.CharField(
        max_length=20,
        choices=RING_FINGER_CHOICES,
        blank=True,
        null=True
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

    created_date = models.DateTimeField(
        auto_now_add=True
    )

    due_date = models.DateField()

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True
    )

    is_starred = models.BooleanField(
        default=False
    )

    completed_date = models.DateField(
        blank=True,
        null=True
    )

    def __str__(self):
        return self.ticket_number


# =========================================================
# Ticket Photo
# =========================================================

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

    def save(self, *args, **kwargs):
        # 先保存图片
        super().save(*args, **kwargs)

        # 再压缩
        if self.image:
            compress_image(self.image.path)

    def __str__(self):
        return self.ticket.ticket_number


# =========================================================
# Note
# =========================================================

class Note(models.Model):

    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name="notes"
    )

    content = models.TextField()

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"Note for {self.ticket.ticket_number}"


# =========================================================
# Status History
# =========================================================

class StatusHistory(models.Model):
    """
    One row per status change on a ticket.
    Powers the 'Status Timeline' card on the ticket detail page.
    """

    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name="status_history"
    )

    status = models.ForeignKey(
        Status,
        on_delete=models.CASCADE
    )

    note = models.CharField(
        max_length=255,
        blank=True
    )

    created_date = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["-created_date"]
        verbose_name_plural = "Status histories"

    def __str__(self):
        return f"{self.ticket.ticket_number} -> {self.status.status}"


# =========================================================
# Audit Log
# =========================================================

class AuditLog(models.Model):

    ACTION_CHOICES = [
        ("CREATE", "Create"),
        ("UPDATE", "Update"),
        ("DELETE", "Delete"),
        ("LOGIN", "Login"),
        ("LOGOUT", "Logout"),
    ]

    user = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    action = models.CharField(
        max_length=20,
        choices=ACTION_CHOICES
    )

    model_name = models.CharField(
        max_length=100
    )

    object_id = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    description = models.TextField()

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        username = (
            self.user.username
            if self.user
            else "System"
        )

        return f"{username} - {self.action} - {self.model_name}"


# =========================================================
# Mold Type
# =========================================================

def validate_mold_word(value):
    """
    Mold Type and Mold Tag rules:

    Valid:
        Ring
        Pendant
        Earring
        Solitaire
        Three-stone
        Hidden-halo

    Invalid:
        Engagement Ring
        Three Stone
        Three_stone
        Three.stone
        Three@stone

    Only letters and hyphens are allowed.
    Spaces are not allowed.
    """

    if not re.fullmatch(
        r"[A-Za-z]+(?:-[A-Za-z]+)*",
        value
    ):
        raise ValidationError(
            "This field must contain one word. "
            "Hyphens are allowed, but spaces and "
            "other symbols are not allowed."
        )


# =========================================================
# Mold Type
# =========================================================

class MoldType(models.Model):

    name = models.CharField(
        max_length=50,
        unique=True,
        validators=[validate_mold_word]
    )

    def save(self, *args, **kwargs):
        # First letter uppercase,
        # everything else lowercase.
        #
        # Examples:
        # engagement -> Engagement
        # ENGAGEMENT -> Engagement
        # three-stone -> Three-stone
        # THREE-STONE -> Three-stone

        self.name = self.name.lower().capitalize()

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


# =========================================================
# Mold Tag
# =========================================================

class MoldTag(models.Model):

    name = models.CharField(
        max_length=50,
        unique=True,
        validators=[validate_mold_word]
    )

    def save(self, *args, **kwargs):
        # First letter uppercase,
        # everything else lowercase.

        self.name = self.name.lower().capitalize()

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


# =========================================================
# Mold
# =========================================================

class Mold(models.Model):

    # -----------------------------------------------------
    # Mold Code / ID
    # Example: M001
    # -----------------------------------------------------

    mold_code = models.CharField(
        max_length=50,
        unique=True
    )

    # -----------------------------------------------------
    # CAD Project / File Name
    # Example: Solitaire_Ring_001
    # -----------------------------------------------------

    file_name = models.CharField(
        max_length=255
    )

    # -----------------------------------------------------
    # Mold Type
    # Example:
    # Ring
    # Pendant
    # Earring
    # -----------------------------------------------------

    type = models.ForeignKey(
        MoldType,
        on_delete=models.PROTECT,
        related_name="molds"
    )

    # -----------------------------------------------------
    # Tags
    #
    # One mold can have:
    # 0 tags
    # 1 tag
    # many tags
    #
    # One tag can also belong to many molds.
    # -----------------------------------------------------

    tags = models.ManyToManyField(
        MoldTag,
        blank=True,
        related_name="molds"
    )

    # -----------------------------------------------------
    # Description
    # Optional
    # -----------------------------------------------------

    description = models.TextField(
        blank=True
    )

    # -----------------------------------------------------
    # Like / Unlike
    # -----------------------------------------------------

    is_liked = models.BooleanField(
        default=False
    )

    # -----------------------------------------------------
    # Mold Photo
    # Every mold must have one photo.
    #
    # Stored in:
    # media/molds/
    # -----------------------------------------------------

    preview_image = models.ImageField(
        upload_to="molds/",
        blank=True,
        null=True
    )

    # -----------------------------------------------------
    # Dates
    # -----------------------------------------------------

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def save(self, *args, **kwargs):
        # Save the image first
        super().save(*args, **kwargs)

        # Compress the image after saving
        if self.preview_image:
            compress_image(self.preview_image.path)

    def __str__(self):
        return f"{self.mold_code} - {self.file_name}"
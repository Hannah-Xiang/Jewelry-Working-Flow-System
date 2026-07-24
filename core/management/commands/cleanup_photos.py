from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import TicketPhoto


class Command(BaseCommand):
    help = "Delete photos from completed tickets older than 180 days."

    def handle(self, *args, **kwargs):

        cutoff = timezone.now().date() - timedelta(days=180)

        photos = TicketPhoto.objects.filter(
            ticket__completed_date__lt=cutoff,
            ticket__status__status="Completed"
        )

        deleted = 0

        for photo in photos:

            if photo.image:

                # 删除硬盘上的图片
                photo.image.delete(save=False)

                # 删除数据库记录
                photo.delete()

                deleted += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Deleted {deleted} old photo(s)."
            )
        )
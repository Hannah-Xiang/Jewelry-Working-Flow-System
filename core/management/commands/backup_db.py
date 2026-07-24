import shutil
from pathlib import Path
from datetime import date, timedelta

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Backup SQLite database and remove backups older than 30 days."

    def handle(self, *args, **kwargs):

        # -----------------------------
        # Project Root
        # -----------------------------
        BASE_DIR = Path(settings.BASE_DIR)

        # SQLite database
        db_path = BASE_DIR / "db.sqlite3"

        if not db_path.exists():
            self.stdout.write(
                self.style.ERROR("Database file not found.")
            )
            return

        # -----------------------------
        # Backup Folder
        # -----------------------------
        backup_dir = BASE_DIR / "backup"
        backup_dir.mkdir(exist_ok=True)

        # -----------------------------
        # Today's Backup
        # -----------------------------
        today = date.today()

        backup_name = f"{today.isoformat()}-db.sqlite3"

        backup_file = backup_dir / backup_name

        shutil.copy2(db_path, backup_file)

        self.stdout.write(
            self.style.SUCCESS(f"Database backed up to {backup_name}")
        )

        # -----------------------------
        # Delete backups older than 30 days
        # -----------------------------
        cutoff = today - timedelta(days=30)

        deleted = 0

        for file in backup_dir.glob("*-db.sqlite3"):

            try:
                file_date = date.fromisoformat(file.stem.replace("-db", ""))

                if file_date < cutoff:
                    file.unlink()
                    deleted += 1

            except Exception:
                # Ignore files with unexpected names
                continue

        self.stdout.write(
            self.style.SUCCESS(f"Deleted {deleted} old backup(s).")
        )
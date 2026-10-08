from pathlib import Path
import shutil

from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import transaction

from core.models import Mold, MoldType, MoldTag


class Command(BaseCommand):

    help = "Delete all existing molds and import molds from E:\\CAD Library"

    SOURCE_FOLDER = Path(r"E:\CAD Library")

    IMAGE_EXTENSIONS = {
        ".png",
        ".jpg",
        ".jpeg",
        ".webp",
        ".bmp",
        ".gif",
        ".tif",
        ".tiff",
    }

    def handle(self, *args, **options):

        self.stdout.write("")
        self.stdout.write(
            self.style.WARNING(
                "=============================================="
            )
        )
        self.stdout.write(
            self.style.WARNING(
                "           MOLD LIBRARY IMPORT"
            )
        )
        self.stdout.write(
            self.style.WARNING(
                "=============================================="
            )
        )
        self.stdout.write("")

        # ==================================================
        # CHECK SOURCE FOLDER
        # ==================================================

        if not self.SOURCE_FOLDER.exists():

            self.stdout.write(
                self.style.ERROR(
                    f"Source folder does not exist:\n"
                    f"{self.SOURCE_FOLDER}"
                )
            )

            return

        if not self.SOURCE_FOLDER.is_dir():

            self.stdout.write(
                self.style.ERROR(
                    f"Source path is not a folder:\n"
                    f"{self.SOURCE_FOLDER}"
                )
            )

            return

        # ==================================================
        # FIND ALL IMAGES
        # ==================================================

        mold_files = []

        for type_folder in sorted(
            self.SOURCE_FOLDER.iterdir(),
            key=lambda path: path.name.lower()
        ):

            if not type_folder.is_dir():
                continue

            mold_type_name = type_folder.name.strip()

            if not mold_type_name:
                continue

            for image_file in sorted(
                type_folder.iterdir(),
                key=lambda path: path.name.lower()
            ):

                if not image_file.is_file():
                    continue

                if image_file.suffix.lower() not in self.IMAGE_EXTENSIONS:
                    continue

                mold_files.append(
                    (mold_type_name, image_file)
                )

        # ==================================================
        # SHOW RESULT
        # ==================================================

        self.stdout.write(
            f"Found {len(mold_files)} image files."
        )

        self.stdout.write("")

        if not mold_files:

            self.stdout.write(
                self.style.WARNING(
                    "No image files were found."
                )
            )

            return

        # ==================================================
        # WARNING
        # ==================================================

        self.stdout.write(
            self.style.WARNING("WARNING:")
        )

        self.stdout.write(
            "This will DELETE ALL existing Mold records."
        )

        self.stdout.write(
            "It will also DELETE ALL files inside:"
        )

        self.stdout.write(
            f"{Path(settings.MEDIA_ROOT) / 'molds'}"
        )

        self.stdout.write("")

        answer = input(
            "Type YES to continue: "
        )

        if answer.strip() != "YES":

            self.stdout.write(
                self.style.WARNING(
                    "Import cancelled."
                )
            )

            return

        self.stdout.write("")

        # ==================================================
        # IMPORT
        # ==================================================

        try:

            with transaction.atomic():

                # ------------------------------------------
                # Delete old Mold records and images
                # ------------------------------------------

                self.delete_existing_molds()

                imported_count = 0
                skipped_count = 0

                type_cache = {}
                tag_cache = {}

                # ------------------------------------------
                # Import every image
                # ------------------------------------------

                for mold_type_name, image_file in mold_files:

                    # ==================================================
                    # ORIGINAL FILE NAME
                    # ==================================================

                    # Keep the complete original filename
                    # without the extension for file_name.
                    #
                    # Example:
                    #
                    # CW014 - EMERALD SOLITAIRE.png
                    #
                    # file_name =
                    # CW014 - EMERALD SOLITAIRE

                    file_name = image_file.stem.strip()

                    if not file_name:

                        skipped_count += 1

                        self.stdout.write(
                            self.style.WARNING(
                                f"Skipped empty filename: "
                                f"{image_file}"
                            )
                        )

                        continue

                    # ==================================================
                    # MOLD TYPE
                    #
                    # Type ALWAYS comes from the folder.
                    #
                    # EARRING -> Earring
                    # RING    -> Ring
                    # pendant -> Pendant
                    # ==================================================

                    normalized_type_name = (
                        mold_type_name
                        .strip()
                        .lower()
                        .capitalize()
                    )

                    # ------------------------------------------
                    # Get or create MoldType
                    # ------------------------------------------

                    if normalized_type_name not in type_cache:

                        mold_type, created = (
                            MoldType.objects.get_or_create(
                                name=normalized_type_name
                            )
                        )

                        type_cache[
                            normalized_type_name
                        ] = mold_type

                    else:

                        mold_type = type_cache[
                            normalized_type_name
                        ]

                    # ==================================================
                    # MOLD CODE
                    #
                    # If "-" exists:
                    #
                    # CW014 - EMERALD SOLITAIRE
                    # -> CW014
                    #
                    # If no "-":
                    #
                    # CW017 PRAYER BEZEL SET RINGS
                    # -> CW017
                    #
                    # DYLAN
                    # -> DYLAN
                    # ==================================================

                    if "-" in file_name:

                        mold_code = (
                            file_name
                            .split("-", 1)[0]
                            .strip()
                        )

                    else:

                        mold_code = (
                            file_name
                            .split(" ", 1)[0]
                            .strip()
                        )

                    if not mold_code:

                        skipped_count += 1

                        self.stdout.write(
                            self.style.WARNING(
                                f"Skipped invalid mold code: "
                                f"{file_name}"
                            )
                        )

                        continue

                    # ==================================================
                    # DUPLICATE MOLD CODE
                    #
                    # If the calculated code already exists,
                    # use the COMPLETE filename without extension.
                    #
                    # Example:
                    #
                    # First:
                    # CW014
                    #
                    # Second:
                    # CW014 - ANOTHER RING
                    #
                    # becomes:
                    # CW014 - ANOTHER RING
                    # ==================================================

                    if Mold.objects.filter(
                        mold_code=mold_code
                    ).exists():

                        mold_code = file_name

                        self.stdout.write(
                            self.style.WARNING(
                                f"Mold code already exists. "
                                f"Using filename instead: "
                                f"{mold_code}"
                            )
                        )

                    # ------------------------------------------
                    # Check again
                    # ------------------------------------------

                    if Mold.objects.filter(
                        mold_code=mold_code
                    ).exists():

                        skipped_count += 1

                        self.stdout.write(
                            self.style.WARNING(
                                f"Skipped duplicate filename: "
                                f"{mold_code}"
                            )
                        )

                        continue

                    # ==================================================
                    # AUTOMATIC TAG
                    #
                    # ENG -> Engagement-ring
                    # WB  -> Wedding-band
                    # FR  -> Fashion-ring
                    #
                    # IMPORTANT:
                    # This changes TAG only.
                    # TYPE still comes from the folder.
                    # ==================================================

                    file_name_upper = file_name.upper()

                    tag_name = None

                    if file_name_upper.startswith("ENG"):

                        tag_name = "Engagement-ring"

                    elif file_name_upper.startswith("WB"):

                        tag_name = "Wedding-band"

                    elif file_name_upper.startswith("FR"):

                        tag_name = "Fashion-ring"

                    # ------------------------------------------
                    # Get or create tag
                    # ------------------------------------------

                    mold_tag = None

                    if tag_name:

                        if tag_name not in tag_cache:

                            mold_tag, created = (
                                MoldTag.objects.get_or_create(
                                    name=tag_name
                                )
                            )

                            tag_cache[tag_name] = mold_tag

                        else:

                            mold_tag = tag_cache[
                                tag_name
                            ]

                    # ==================================================
                    # CREATE MOLD
                    # ==================================================

                    mold = Mold.objects.create(

                        mold_code=mold_code,

                        file_name=file_name,

                        type=mold_type,

                        description="",

                        is_liked=False,

                    )

                    # ==================================================
                    # ADD AUTOMATIC TAG
                    # ==================================================

                    if mold_tag:

                        mold.tags.add(mold_tag)

                    # ==================================================
                    # COPY IMAGE
                    # ==================================================

                    self.copy_image_to_mold(
                        mold=mold,
                        image_file=image_file
                    )

                    imported_count += 1

                    # ------------------------------------------
                    # Display result
                    # ------------------------------------------

                    if tag_name:

                        self.stdout.write(
                            self.style.SUCCESS(
                                f"Imported: "
                                f"{mold_code} "
                                f"-> {normalized_type_name} "
                                f"[Tag: {tag_name}]"
                            )
                        )

                    else:

                        self.stdout.write(
                            self.style.SUCCESS(
                                f"Imported: "
                                f"{mold_code} "
                                f"-> {normalized_type_name}"
                            )
                        )

                # ==================================================
                # SUMMARY
                # ==================================================

                self.stdout.write("")

                self.stdout.write(
                    "----------------------------------------------"
                )

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Imported: {imported_count}"
                    )
                )

                self.stdout.write(
                    self.style.WARNING(
                        f"Skipped: {skipped_count}"
                    )
                )

                self.stdout.write(
                    f"Mold types used: {len(type_cache)}"
                )

                self.stdout.write(
                    f"Automatic tags used: {len(tag_cache)}"
                )

                self.stdout.write(
                    "----------------------------------------------"
                )

        except Exception as e:

            self.stdout.write("")

            self.stdout.write(
                self.style.ERROR(
                    "IMPORT FAILED"
                )
            )

            self.stdout.write(
                self.style.ERROR(
                    str(e)
                )
            )

            raise

        self.stdout.write("")

        self.stdout.write(
            self.style.SUCCESS(
                "Mold import completed successfully."
            )
        )

    # ==================================================
    # DELETE OLD MOLDS + OLD MOLD IMAGES
    # ==================================================

    def delete_existing_molds(self):

        # ------------------------------------------
        # 1. Delete all Mold database records
        # ------------------------------------------

        existing_molds = Mold.objects.all()

        count = existing_molds.count()

        self.stdout.write(
            f"Deleting {count} existing mold records..."
        )

        existing_molds.delete()

        self.stdout.write(
            self.style.SUCCESS(
                "All mold records deleted."
            )
        )

        # ------------------------------------------
        # 2. Delete everything inside media/molds/
        # ------------------------------------------

        mold_media_folder = (
            Path(settings.MEDIA_ROOT) / "molds"
        )

        if not mold_media_folder.exists():

            self.stdout.write(
                "media/molds/ does not exist."
            )

            return

        deleted_count = 0

        for item in mold_media_folder.iterdir():

            # --------------------------------------
            # Delete files
            # --------------------------------------

            if item.is_file():

                try:

                    item.unlink()

                    deleted_count += 1

                except Exception as e:

                    self.stdout.write(
                        self.style.WARNING(
                            f"Could not delete "
                            f"{item.name}: {e}"
                        )
                    )

            # --------------------------------------
            # Delete folders
            # --------------------------------------

            elif item.is_dir():

                try:

                    shutil.rmtree(item)

                    deleted_count += 1

                except Exception as e:

                    self.stdout.write(
                        self.style.WARNING(
                            f"Could not delete folder "
                            f"{item.name}: {e}"
                        )
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f"Deleted {deleted_count} "
                f"files/folders from media/molds/."
            )
        )

    # ==================================================
    # COPY IMAGE
    # ==================================================

    def copy_image_to_mold(
        self,
        mold,
        image_file
    ):

        mold_media_folder = (
            Path(settings.MEDIA_ROOT) / "molds"
        )

        mold_media_folder.mkdir(
            parents=True,
            exist_ok=True
        )

        # ==================================================
        # IMPORTANT:
        # KEEP THE ORIGINAL IMAGE NAME
        # ==================================================
        #
        # Example:
        #
        # Original:
        # WB048 - SOME BAND.png
        #
        # Saved:
        # WB048 - SOME BAND.png
        #
        # NOT:
        # WB048.png
        #
        # Mold code and image filename are independent.
        # ==================================================

        destination_name = image_file.name

        destination = (
            mold_media_folder / destination_name
        )

        # ------------------------------------------
        # Copy image
        # ------------------------------------------

        shutil.copy2(
            image_file,
            destination
        )

        # ------------------------------------------
        # Save original image path to database
        # ------------------------------------------

        mold.preview_image = (
            f"molds/{destination_name}"
        )

        mold.save(
            update_fields=[
                "preview_image",
                "updated_at"
            ]
        )
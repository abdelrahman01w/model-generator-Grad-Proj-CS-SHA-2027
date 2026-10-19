import json
import hashlib
from pathlib import Path
from collections import defaultdict
from itertools import combinations

import imagehash
from PIL import Image, UnidentifiedImageError

# 1. CONFIGURATION

PROJECT_ROOT = Path(__file__).resolve().parents[4]
CONFIG_PATH = PROJECT_ROOT / "assets" / "classes_config.json"


MIN_IMAGES_PER_CLASS = 100
MAX_IMAGES_PER_CLASS = 1000

# Smaller pHash distance means greater visual similarity.
PHASH_THRESHOLD = 5

IMAGE_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".bmp",
    ".webp", ".tif", ".tiff"
}

VALID_FORMATS = {
    "JPEG", "PNG", "BMP", "WEBP", "TIFF"
}


# ============================================================
# 2. VALIDATION STATISTICS
# ============================================================

warnings = []
valid_images = []

total_checked = 0
total_valid = 0
total_invalid = 0

# ============================================================
# 3. WARNING HELPER
# ============================================================

def add_warning(category, path, details, related_path=None):
    """Print and record a warning without modifying any files."""

    warning = {
        "category": category,
        "path": str(path),
        "details": details,
        "related_path": (
            str(related_path) if related_path is not None else ""
        )
    }

    warnings.append(warning)

    print(f"\nWARNING [{category}]")
    print(f"Path: {path}")
    print(f"Details: {details}")

    if related_path is not None:
        print(f"Related image: {related_path}")


# ============================================================
# 4. LOAD CLASSES FROM YOUR JSON
# ============================================================

def load_classes(config_path):
    if not config_path.is_file():
        raise FileNotFoundError(
            f"JSON configuration not found: {config_path}"
        )

    with open(config_path, "r", encoding="utf-8") as file:
        classes = json.load(file)

    if not isinstance(classes, dict) or not classes:
        raise ValueError(
            "Expected a JSON dictionary containing class names and paths."
        )

    for class_name, folder_path in classes.items():
        if not isinstance(class_name, str) or not class_name.strip():
            raise ValueError(f"Invalid class name: {class_name!r}")

        if not isinstance(folder_path, str) or not folder_path.strip():
            raise ValueError(
                f"Invalid folder path for {class_name!r}"
            )

    return classes


# ============================================================
# 5. FIND IMAGES IN EACH CLASS FOLDER
# ============================================================

def find_class_images(classes):
    images_by_class = {}
    for class_name, folder_path in classes.items():
        folder = Path(folder_path)

        if not folder.exists():
            add_warning(
                "CLASS_FOLDER_MISSING",
                folder,
                f"The folder for {class_name} does not exist."
            )
            images_by_class[class_name] = []
            continue

        if not folder.is_dir():
            add_warning(
                "PATH_NOT_A_DIRECTORY",
                folder,
                f"The path for {class_name} is not a folder."
            )
            images_by_class[class_name] = []
            continue

        image_paths = sorted(
            path for path in folder.rglob("*")
            if path.is_file()
            and path.suffix.lower() in IMAGE_EXTENSIONS
        )

        images_by_class[class_name] = image_paths

    return images_by_class


# ============================================================
# 6. EXACT DUPLICATE HASH
# ============================================================

def calculate_sha256(path):
    """Calculate a hash of the exact file contents."""

    digest = hashlib.sha256()

    with open(path, "rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


# ============================================================
# 7. IMAGE INTEGRITY AND DIMENSION VALIDATION
# ============================================================

def validate_image(path, class_name):
    global total_checked
    global total_valid
    global total_invalid

    total_checked += 1

    try:
        if path.stat().st_size == 0:
            total_invalid += 1
            add_warning("EMPTY_FILE", path, "File size is zero bytes.")
            return

        # Verify the image structure.
        with Image.open(path) as img:
            image_format = img.format
            img.verify()

        if image_format not in VALID_FORMATS:
            total_invalid += 1
            add_warning(
                "UNSUPPORTED_FORMAT",
                path,
                f"Detected image format: {image_format}"
            )
            return

        # Decode the image to ensure its pixel data is readable.
        with Image.open(path) as img:
            img.load()

        total_valid += 1

        # Fingerprints are calculated only for readable images.
        sha256 = calculate_sha256(path)

        with Image.open(path) as img:
            phash = imagehash.phash(img.convert("RGB"))

        valid_images.append({
            "path": path,
            "class_name": class_name,
            "format": image_format,
            "sha256": sha256,
            "phash": phash
        })

    except (
        UnidentifiedImageError,
        OSError,
        SyntaxError,
        ValueError
    ) as error:
        total_invalid += 1

        add_warning(
            "CORRUPTED_OR_UNREADABLE",
            path,
            str(error)
        )

    except Exception as error:
        total_invalid += 1

        add_warning(
            "VALIDATION_ERROR",
            path,
            f"{type(error).__name__}: {error}"
        )


# ============================================================
# 8. EXACT DUPLICATE DETECTION
# ============================================================

def detect_exact_duplicates(images):
    hash_groups = defaultdict(list)

    for image in images:
        hash_groups[image["sha256"]].append(image)

    duplicate_groups = {
        sha256: group
        for sha256, group in hash_groups.items()
        if len(group) > 1
    }

    for sha256, group in duplicate_groups.items():
        for image in group:
            other_paths = [
                str(other["path"])
                for other in group
                if other["path"] != image["path"]
            ]

            add_warning(
                "EXACT_DUPLICATE",
                image["path"],
                f"SHA-256: {sha256}. Identical copies: "
                + ", ".join(other_paths)
            )

        group_classes = {
            image["class_name"] for image in group
        }

        if len(group_classes) > 1:
            for image in group:
                add_warning(
                    "DUPLICATE_ACROSS_CLASSES",
                    image["path"],
                    "Identical file contents appear in classes: "
                    + ", ".join(sorted(group_classes))
                )

    return duplicate_groups


# ============================================================
# 9. VISUAL SIMILARITY DETECTION
# ============================================================

def detect_visual_similarity(images):
    similar_pairs = []

    for image_a, image_b in combinations(images, 2):
        distance = image_a["phash"] - image_b["phash"]

        if distance <= PHASH_THRESHOLD:
            similar_pairs.append((image_a, image_b, distance))

            add_warning(
                "POSSIBLE_VISUAL_DUPLICATE",
                image_a["path"],
                f"pHash distance: {distance}; "
                f"threshold: {PHASH_THRESHOLD}",
                related_path=image_b["path"]
            )

            if image_a["class_name"] != image_b["class_name"]:
                add_warning(
                    "VISUALLY_SIMILAR_ACROSS_CLASSES",
                    image_a["path"],
                    f"Classes differ: {image_a['class_name']} vs "
                    f"{image_b['class_name']}",
                    related_path=image_b["path"]
                )

    return similar_pairs


# ============================================================
# 10. CLASS IMAGE COUNT VALIDATION
# ============================================================

def validate_class_counts(images_by_class):
    class_counts = {}

    print("\n" + "=" * 65)
    print("IMAGE COUNT PER CLASS")
    print("=" * 65)

    for class_name, paths in images_by_class.items():
        count = len(paths)
        class_counts[class_name] = count

        print(f"{class_name}: {count} image files")

        if count < MIN_IMAGES_PER_CLASS:
            add_warning(
                "CLASS_BELOW_MINIMUM",
                class_name,
                f"{count} images; minimum is {MIN_IMAGES_PER_CLASS}."
            )

        elif count > MAX_IMAGES_PER_CLASS:
            add_warning(
                "CLASS_ABOVE_MAXIMUM",
                class_name,
                f"{count} images; maximum is {MAX_IMAGES_PER_CLASS}."
            )

    return class_counts


# ============================================================
# 11. FINAL CONSOLE SUMMARY
# ============================================================

def print_final_summary(
    classes,
    class_counts,
    duplicate_groups,
    similar_pairs
):
    below_minimum = sum(
        count < MIN_IMAGES_PER_CLASS
        for count in class_counts.values()
    )

    above_maximum = sum(
        count > MAX_IMAGES_PER_CLASS
        for count in class_counts.values()
    )

    within_limits = sum(
        MIN_IMAGES_PER_CLASS <= count <= MAX_IMAGES_PER_CLASS
        for count in class_counts.values()
    )

    print("\n")
    print("=" * 65)
    print("FINAL DATASET VALIDATION SUMMARY")
    print("=" * 65)

    print(f"Configured classes:             {len(classes)}")
    print(f"Total image files checked:      {total_checked}")
    print(f"Valid images:                   {total_valid}")
    print(f"Invalid images:                 {total_invalid}")
    print(f"Exact duplicate groups:         {len(duplicate_groups)}")
    print(f"Possible similar image pairs:   {len(similar_pairs)}")
    print(f"Total warnings recorded:        {len(warnings)}")

    print("\nClass count summary:")
    print(f"Classes below minimum:          {below_minimum}")
    print(f"Classes above maximum:          {above_maximum}")
    print(f"Classes within limits:          {within_limits}")

    print("\nWarnings by category:")

    warning_counts = defaultdict(int)

    for warning in warnings:
        warning_counts[warning["category"]] += 1

    if warning_counts:
        for category, count in sorted(warning_counts.items()):
            print(f"{category}: {count}")
    else:
        print("No warnings.")

    print("\nNo images were deleted, moved, or modified.")
    print("=" * 65)


# ============================================================
# 12. MAIN
# ============================================================

def main():
    print("Starting image validation...\n")

    classes = load_classes(CONFIG_PATH)

    print(f"Configured classes: {len(classes)}")

    images_by_class = find_class_images(classes)

    print("\nChecking image integrity and dimensions...")

    for class_name, paths in images_by_class.items():
        print(f"\nChecking {class_name}: {len(paths)} image files")

        for index, path in enumerate(paths, start=1):
            print(
                f"\rProgress: {index}/{len(paths)}",
                end="",
                flush=True
            )

            validate_image(path, class_name)

        if paths:
            print()

    print("\nChecking exact duplicates...")
    duplicate_groups = detect_exact_duplicates(valid_images)

    print("\nChecking visual similarity...")
    similar_pairs = detect_visual_similarity(valid_images)

    print("\nChecking class image counts...")
    class_counts = validate_class_counts(images_by_class)

    print_final_summary(
        classes,
        class_counts,
        duplicate_groups,
        similar_pairs
    )


if __name__ == "__main__":
    try:
        main()
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as error:
        print(f"\nERROR: {error}")
    except PermissionError as error:
        print(f"\nERROR: Permission denied: {error}")

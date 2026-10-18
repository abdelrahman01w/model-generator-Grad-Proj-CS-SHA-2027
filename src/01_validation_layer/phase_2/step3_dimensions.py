import statistics
import sys
from collections import Counter

from PIL import Image

from common import Reporter, images_by_class, load_classes, print_table, save_report

#settings
STEP_NAME = "dimensions"
CLASS_SIZE_RATIO_WARN = 1.5  # warn if one class has images 1.5x bigger than another
LIST_LIMIT = 20              # max number of file paths we print in a list
ALL = "(all)"                # name of the row that combines every class
TOP_SIZES = 3                # how many of the most common sizes we show per class


#reading images
def read_image_info(path):
    """Open ONE image and return (width, height, mode).
    Returns None if the file cannot be opened as an image."""
    try:
        with Image.open(path) as img:
            return img.width, img.height, img.mode
    except (OSError, ValueError, Image.DecompressionBombError):
        return None


def collect_dimensions(images):
    """Read every image. Returns two dictionaries:
       records[label]    -> list of {"width", "height", "mode"} for the readable images
       unreadable[label] -> list of paths we could not open"""
    records = {}
    unreadable = {}

    for label, paths in images.items():
        records[label] = []
        unreadable[label] = []

        for path in paths:
            info = read_image_info(path)
            if info is None:
                unreadable[label].append(path)
            else:
                width, height, mode = info
                records[label].append({"width": width, "height": height, "mode": mode})

    return records, unreadable


#statistics
def describe(values):
    """min / max / mean / median of a list of numbers."""
    return {
        "min": min(values),
        "max": max(values),
        "mean": statistics.mean(values),
        "median": float(statistics.median(values)),
    }


def summarize(records):
    """Turn a list of image records into the statistics we report.
    Returns None if the list is empty."""
    if len(records) == 0:
        return None

    # Build simple lists with one value per image
    widths = []
    heights = []
    ratios = []   # aspect ratio = width / height (1.0 means a square image)
    pixels = []   # width * height = how big the image is
    for r in records:
        widths.append(r["width"])
        heights.append(r["height"])
        ratios.append(r["width"] / r["height"])
        pixels.append(r["width"] * r["height"])

    # Count how many images have each (width, height) pair and each mode
    size_counts = Counter()
    mode_counts = Counter()
    for r in records:
        size_counts[(r["width"], r["height"])] += 1
        mode_counts[r["mode"]] += 1

    (top_w, top_h), top_count = size_counts.most_common(1)[0]

    # The most common sizes, each with its share of the images (in %)
    top_sizes = []
    for (w, h), count in size_counts.most_common(TOP_SIZES):
        top_sizes.append([w, h, 100.0 * count / len(records)])

    return {
        "images": len(records),
        "width": describe(widths),
        "height": describe(heights),
        "aspect_ratio": describe(ratios),
        "median_pixels": statistics.median(pixels),
        "unique_sizes": len(size_counts),
        "most_common_size": [top_w, top_h],
        "most_common_share": 100.0 * top_count / len(records),
        "top_sizes": top_sizes,
        "modes": dict(mode_counts),
    }


#printing
def print_stat_table(title, summaries, key):
    """Print one table (min / max / mean / median) for 'width', 'height' or 'aspect_ratio'."""
    print(f"\n{title}")
    rows = []
    for label, s in summaries.items():
        d = s[key]
        rows.append([label, s["images"], d["min"], d["max"], d["mean"], d["median"]])
    print_table(["label", "images", "min", "max", "mean", "median"], rows)


def print_size_table(summaries):
    """Print the number of unique sizes and the most common sizes of each class."""
    print(f"\nUnique sizes and the {TOP_SIZES} most common sizes (width x height, % of the class):")
    rows = []
    for label, s in summaries.items():
        row = [label, s["unique_sizes"]]
        covered = 0.0  # how much of the class the top sizes cover together
        for i in range(TOP_SIZES):
            if i < len(s["top_sizes"]):
                w, h, share = s["top_sizes"][i]
                row.append(f"{w}x{h} ({share:.1f}%)")
                covered += share
            else:
                row.append("-")  # this class has fewer than TOP_SIZES different sizes
        row.append(covered)
        rows.append(row)

    headers = ["label", "unique sizes"]
    for i in range(TOP_SIZES):
        headers.append(f"#{i + 1}")
    headers.append(f"top {TOP_SIZES} cover %")
    print_table(headers, rows)


def print_mode_table(summaries):
    """Print how many images use each color mode (one row per mode)."""
    print("\nColor modes:")
    all_modes = set()
    for s in summaries.values():
        for mode in s["modes"]:
            all_modes.add(mode)

    labels = list(summaries)
    rows = []
    for mode in sorted(all_modes):
        row = [mode]
        for label in labels:
            row.append(summaries[label]["modes"].get(mode, 0))
        rows.append(row)
    print_table(["mode"] + labels, rows)


#checks
def check_unreadable(rep, unreadable):
    """FAIL for every image that Pillow could not open."""
    found_any = False
    for label, paths in unreadable.items():
        if len(paths) == 0:
            continue
        found_any = True
        rep.fail(f"[{label}] {len(paths)} image(s) could not be opened:")
        for p in paths[:LIST_LIMIT]:
            print(f"         {p}")
        if len(paths) > LIST_LIMIT:
            print(f"         ... and {len(paths) - LIST_LIMIT} more")
    if not found_any:
        rep.ok("All images could be opened")


def check_size_uniformity(rep, total):
    """PASS if every image has the same size, otherwise WARN."""
    w, h = total["most_common_size"]
    if total["unique_sizes"] == 1:
        rep.ok(f"All images have the same size: {w}x{h}")
    else:
        rep.warn(f"Sizes are not uniform: {total['unique_sizes']} different sizes "
                 f"(most common is {w}x{h}, {total['most_common_share']:.1f}% of images). "
                 "Images will need resizing before training.")


def check_modes(rep, total, class_summaries):
    """Check that every image has the same color mode, in every class."""
    if len(total["modes"]) == 1:
        mode = list(total["modes"])[0]
        rep.ok(f"All images use the same color mode: {mode}")
    else:
        rep.warn(f"Mixed color modes: {total['modes']}. "
                 "They need converting to one mode (e.g. RGB) before training.")

    # Does each class use the same set of modes as the first class?
    labels = list(class_summaries)
    first_modes = set(class_summaries[labels[0]]["modes"])
    for label in labels[1:]:
        if set(class_summaries[label]["modes"]) != first_modes:
            rep.warn(f"Class [{label}] uses different color modes than [{labels[0]}]")


def check_class_sizes(rep, class_summaries):
    """Compare the typical image size (in pixels) between classes."""
    medians = {}
    for label, s in class_summaries.items():
        medians[label] = s["median_pixels"]

    smallest_value = min(medians.values())
    largest_value = max(medians.values())
    ratio = largest_value / smallest_value

    # Classes with the smallest typical size (can be more than one if they tie)
    smallest = [label for label, m in medians.items() if m == smallest_value]
    # Every class whose typical size is more than the allowed ratio above the smallest
    too_big = [label for label, m in medians.items()
               if m / smallest_value > CLASS_SIZE_RATIO_WARN]

    if len(too_big) > 0:
        rep.warn(f"Typical image size differs between classes: {', '.join(too_big)} are more than "
                 f"{CLASS_SIZE_RATIO_WARN}x bigger (in pixels) than {', '.join(smallest)} "
                 f"(largest/smallest = {ratio:.2f}). "
                 "A model could learn the image size instead of the disease.")
    else:
        rep.ok(f"Classes have similar image sizes (largest/smallest = {ratio:.2f}, "
               f"limit {CLASS_SIZE_RATIO_WARN})")
    return ratio


# run
def run(arg=None):
    """Returns (data, reporter), or (None, reporter) if the input is unusable."""
    rep = Reporter(STEP_NAME)

    # 1. Find the class folders (from classes_config.json by default)
    rep.section("Input")
    classes = load_classes(rep, arg)
    if classes is None:
        rep.summary()
        return None, rep
    rep.ok(f"Loaded {len(classes)} classes")

    # 2. List the images and read their sizes
    images = images_by_class(classes)
    total_files = sum(len(paths) for paths in images.values())
    rep.info(f"Reading the headers of {total_files:,} images...")
    records, unreadable = collect_dimensions(images)

    # 3. Compute statistics per class, and for all classes together
    class_summaries = {}
    all_records = []
    for label in classes:
        summary = summarize(records[label])
        if summary is not None:
            class_summaries[label] = summary
        all_records.extend(records[label])

    total = summarize(all_records)
    if total is None:
        rep.fail("No readable images found")
        rep.summary()
        return None, rep

    # The tables show every class and then the combined "(all)" row
    table_data = dict(class_summaries)
    table_data[ALL] = total

    # 4. Print the tables
    rep.section("1. Image dimensions")
    print_stat_table("Width (pixels):", table_data, "width")
    print_stat_table("Height (pixels):", table_data, "height")
    print_stat_table("Aspect ratio (width / height):", table_data, "aspect_ratio")
    print_size_table(table_data)
    print_mode_table(table_data)

    # 5. Run the checks
    rep.section("2. Checks")
    check_unreadable(rep, unreadable)
    check_size_uniformity(rep, total)
    check_modes(rep, total, class_summaries)
    ratio = check_class_sizes(rep, class_summaries)

    # 6. Save the results as JSON (outside the dataset) for the final summary
    data = {
        "per_class": class_summaries,
        "overall": total,
        "class_size_ratio": ratio,
        "unreadable": {label: [str(p) for p in paths]
                       for label, paths in unreadable.items() if paths},
    }
    save_report(rep, classes, data)
    rep.summary()
    return data, rep


if __name__ == "__main__":
    _, reporter = run(sys.argv[1] if len(sys.argv) > 1 else None)
    sys.exit(reporter.exit_code())
import statistics
import sys
from collections import Counter

from common import (
    IMAGE_EXTS,
    Reporter,
    is_image,
    load_classes,
    pct,
    print_table,
    save_report,
    walk_files,
)


BALANCED_MAX = 1.5 
MILD_MAX = 3.0
TINY_BYTES = 1024    # image files smaller than this are suspicious
LIST_LIMIT = 20      # max file paths printed per list

STEP_NAME = "class_stats"


#helpers
def show_paths(paths):
    for p in paths[:LIST_LIMIT]:
        print(f"         {p}")
    if len(paths) > LIST_LIMIT:
        print(f"         ... and {len(paths) - LIST_LIMIT} more")


def size_stats(sizes):
    """Size statistics in bytes, or None for an empty list."""
    if not sizes:
        return None
    return {
        "min": min(sizes),
        "max": max(sizes),
        "mean": statistics.mean(sizes),
        "median": statistics.median(sizes),
        "total": sum(sizes),
    }


#section 1
def collect_inventory(rep, classes):
    """Walk every class folder once and collect file metadata (no image is opened)."""
    inventory = {}
    for label, folder in classes.items():
        ext_counts = Counter()
        variants = {}
        images, non_images, zero_byte, tiny, sizes = 0, [], [], [], []

        for p in walk_files(folder):
            raw = p.suffix
            ext = raw.lower() if raw else "(none)"
            ext_counts[ext] += 1
            variants.setdefault(ext, set()).add(raw if raw else "(none)")

            try:
                size = p.stat().st_size
            except OSError as e:
                rep.fail(f"[{label}] cannot read file info: {p} ({e})")
                continue

            if size == 0:
                zero_byte.append(p)
            if is_image(p):
                images += 1
                sizes.append(size)
                if 0 < size < TINY_BYTES:
                    tiny.append(p)
            else:
                non_images.append(p)

        inventory[label] = {
            "images": images,
            "ext_counts": ext_counts,
            "variants": variants,
            "non_images": non_images,
            "zero_byte": zero_byte,
            "tiny": tiny,
            "sizes": size_stats(sizes),
        }
    return inventory


def report_inventory(rep, classes, inventory):
    rep.section("1. File inventory")
    labels = list(classes)

    # files per extension (overall + per class)
    all_exts = sorted({e for inv in inventory.values() for e in inv["ext_counts"]})
    rows = []
    for ext in all_exts:
        per_class = [inventory[l]["ext_counts"].get(ext, 0) for l in labels]
        rows.append([ext, sum(per_class)] + per_class)
    print("\nFiles per extension:")
    print_table(["extension", "total"] + labels, rows)

    image_exts = sorted(e for e in all_exts if e in IMAGE_EXTS)
    if len(image_exts) > 1:
        rep.info(f"Image formats used: {', '.join(image_exts)}")
    else:
        rep.ok(f"Single image format: {', '.join(image_exts) if image_exts else 'none'}")

    # extension case variants (.jpg vs .JPG), merged in the table above
    variants = {}
    for label in labels:
        for ext, found in inventory[label]["variants"].items():
            variants.setdefault(ext, set()).update(found)
    for ext, found in sorted(variants.items()):
        if len(found) > 1:
            rep.info(f"Extension written in different cases (merged as {ext}): {sorted(found)}")

    # file sizes
    print("\nImage file sizes (KB):")
    rows = []
    for label in labels:
        s = inventory[label]["sizes"]
        if s:
            rows.append([label, inventory[label]["images"], s["min"] / 1024, s["max"] / 1024,
                         s["mean"] / 1024, s["median"] / 1024, s["total"] / (1024 * 1024)])
    print_table(["label", "images", "min", "max", "mean", "median", "total MB"], rows)

    # problems
    print()
    any_non_image = any_zero = any_tiny = False
    for label in labels:
        inv = inventory[label]
        if inv["non_images"]:
            any_non_image = True
            rep.warn(f"[{label}] {len(inv['non_images'])} non-image file(s):")
            show_paths(inv["non_images"])
        if inv["zero_byte"]:
            any_zero = True
            rep.fail(f"[{label}] {len(inv['zero_byte'])} zero-byte file(s):")
            show_paths(inv["zero_byte"])
        if inv["tiny"]:
            any_tiny = True
            rep.warn(f"[{label}] {len(inv['tiny'])} image(s) under {TINY_BYTES} bytes "
                     "(possibly broken):")
            show_paths(inv["tiny"])
    if not any_non_image:
        rep.ok("No non-image files found")
    if not any_zero:
        rep.ok("No zero-byte files found")
    if not any_tiny:
        rep.ok(f"No suspiciously small images (under {TINY_BYTES} bytes)")


#section 2
def verdict_for(ratio):
    if ratio < BALANCED_MAX:
        return "balanced"
    if ratio <= MILD_MAX:
        return "mild imbalance"
    return "significant imbalance"


def report_class_counts(rep, classes, inventory):
    rep.section("2. Class counts")
    counts = {label: inventory[label]["images"] for label in classes}
    total = sum(counts.values())

    if total == 0:
        rep.fail("No images found in any class")
        return {"counts": counts, "total": 0}

    rows = [[label, classes[label].name, n, pct(n, total)] for label, n in counts.items()]
    rows.append(["TOTAL", "", total, 100.0])
    print_table(["label", "folder", "images", "percent"], rows)

    values = list(counts.values())
    largest = max(counts, key=counts.get)
    smallest = min(counts, key=counts.get)
    median = statistics.median(values)
    print()
    rep.info(f"Classes: {len(counts)} | expected share if balanced: {100 / len(counts):.2f}% each")
    rep.info(f"Largest : {largest} ({counts[largest]:,} images)")
    rep.info(f"Smallest: {smallest} ({counts[smallest]:,} images)")

    ratio_min = ratio_med = verdict = None
    if counts[smallest] == 0:
        rep.fail(f"Class [{smallest}] has no images; the imbalance ratio is infinite")
    else:
        ratio_min = counts[largest] / counts[smallest]
        ratio_med = counts[largest] / median if median else None
        verdict = verdict_for(ratio_min)
        med_text = f"{ratio_med:.2f}" if ratio_med is not None else "n/a"
        rep.info(f"Imbalance ratio: max/min = {ratio_min:.2f}, max/median = {med_text}")
        msg = (f"Class balance: {verdict} (max/min = {ratio_min:.2f}; thresholds: "
               f"< {BALANCED_MAX} balanced, <= {MILD_MAX} mild, above = significant)")
        if verdict == "balanced":
            rep.ok(msg)
        else:
            rep.warn(msg)

    return {
        "counts": counts,
        "percent": {label: pct(n, total) for label, n in counts.items()},
        "total": total,
        "largest": largest,
        "smallest": smallest,
        "median": median,
        "imbalance_max_min": ratio_min,
        "imbalance_max_median": ratio_med,
        "verdict": verdict,
        "thresholds": {"balanced_below": BALANCED_MAX, "mild_up_to": MILD_MAX},
    }


#run
def run(arg=None):
    """Returns (data, reporter), or (None, reporter) if the input is unusable."""
    rep = Reporter(STEP_NAME)

    rep.section("Input")
    classes = load_classes(rep, arg)
    if classes is None:
        rep.summary()
        return None, rep
    rep.ok(f"Loaded {len(classes)} classes")

    inventory = collect_inventory(rep, classes)
    report_inventory(rep, classes, inventory)
    class_data = report_class_counts(rep, classes, inventory)

    data = {
        "classes": {label: str(folder) for label, folder in classes.items()},
        "inventory": {
            label: {
                "extensions": dict(inv["ext_counts"]),
                "non_image_files": [str(p) for p in inv["non_images"]],
                "zero_byte_files": [str(p) for p in inv["zero_byte"]],
                "tiny_images": [str(p) for p in inv["tiny"]],
                "image_size_bytes": inv["sizes"],
            }
            for label, inv in inventory.items()
        },
        "class_stats": class_data,
    }

    save_report(rep, classes, data)
    rep.summary()
    return data, rep


if __name__ == "__main__":
    _, reporter = run(sys.argv[1] if len(sys.argv) > 1 else None)
    sys.exit(reporter.exit_code())
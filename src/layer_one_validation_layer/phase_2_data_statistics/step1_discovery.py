import json
import sys
from pathlib import Path

from common import (
    Reporter,
    default_config_path,
    print_table,
    save_report,
)


MIN_CLASSES = 2
MAX_EXAMPLES = 3  # how many example paths to show per problem


def discover(arg):
    
    rep = Reporter("discovery")

    # input file
    rep.section("Input")

    target = Path(arg).expanduser()

    if not target.is_file():
        rep.fail(f"Input file not found: {target} (quote the path if it has spaces)")
        rep.summary()
        return None, rep

    try:
        with open(target, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        rep.fail(f"Could not read the input file: {e}")
        rep.summary()
        return None, rep

    rep.ok(f"Valid JSON: {target}")

    if not isinstance(data, dict):
        rep.fail("Input must be a JSON object.")
        rep.summary()
        return None, rep

    clean = data.get("clean_dataset")

    if not isinstance(clean, dict) or not clean:
        rep.fail("Input must contain a non-empty 'clean_dataset' object.")
        rep.summary()
        return None, rep

    rep.ok("'clean_dataset' found")

    # classes
    rep.section("Classes")

    if len(clean) < MIN_CLASSES:
        rep.fail(f"Only {len(clean)} class(es); at least {MIN_CLASSES} are required")
    else:
        rep.ok(f"{len(clean)} classes (minimum {MIN_CLASSES})")

    stats = {}
    rows = []
    seen = {}  # path -> first class that listed it (to spot duplicates)

    for label, image_paths in sorted(clean.items()):
        if not label.strip():
            rep.fail("Found a class with an empty name")
            continue

        if not isinstance(image_paths, list) or not image_paths:
            rep.fail(f"[{label}] is empty (needs a non-empty list of image paths)")
            stats[label] = {"images": 0, "missing": 0}
            rows.append((label, 0, 0))
            continue

        missing = []
        duplicates = []

        for value in image_paths:
            if not isinstance(value, str) or not value.strip():
                missing.append(repr(value))
                continue

            if value in seen:
                duplicates.append(value)
            else:
                seen[value] = label

            if not Path(value).expanduser().is_file():
                missing.append(value)

        stats[label] = {"images": len(image_paths), "missing": len(missing)}
        rows.append((label, len(image_paths), len(missing)))

        if missing:
            rep.fail(
                f"[{label}] {len(missing)} of {len(image_paths)} "
                f"listed file(s) missing. e.g. {missing[:MAX_EXAMPLES]}"
            )

        if duplicates:
            rep.warn(
                f"[{label}] {len(duplicates)} path(s) already listed earlier "
                f"(in this class or another). e.g. {duplicates[:MAX_EXAMPLES]}"
            )

    print()
    print_table(["class", "images", "missing"], rows)

    # summary
    rep.section("Summary")

    total = sum(s["images"] for s in stats.values())
    total_missing = sum(s["missing"] for s in stats.values())

    rep.info(f"Classes checked: {len(stats)} of {len(clean)}")
    rep.info(f"Images listed: {total:,} ({total_missing:,} missing)")

    if not total_missing and stats and all(s["images"] for s in stats.values()):
        rep.ok("All listed image files exist")

    save_report(rep, stats)
    rep.summary()

    return (stats if not rep.counts["FAIL"] else None), rep


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else str(default_config_path())

    results, reporter = discover(arg)

    sys.exit(reporter.exit_code())
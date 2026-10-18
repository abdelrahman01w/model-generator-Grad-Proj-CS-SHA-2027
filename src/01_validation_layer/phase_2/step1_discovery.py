import json
import sys
from pathlib import Path

from common import (
    IGNORED_NAMES,
    MIN_CLASSES,
    Reporter,
    default_config_path,
    is_image,
    normalize,
    list_children,
    resolve_root,
    resolve_class_folder,
    save_report,
)


# scanning
def scan_folder(folder):
    """Recursively count images and other files inside one class folder."""
    direct = nested = other = 0
    subdirs = []

    for p in folder.rglob("*"):
        rel_parts = p.relative_to(folder).parts

        if any(
            part.lower() in IGNORED_NAMES or part.startswith(".")
            for part in rel_parts
        ):
            continue

        if p.is_dir():
            if p.parent == folder:
                subdirs.append(p.name)

        elif p.is_file():
            if is_image(p):
                if p.parent == folder:
                    direct += 1
                else:
                    nested += 1
            else:
                other += 1

    return {
        "direct": direct,
        "nested": nested,
        "other": other,
        "subdirs": subdirs,
    }


# input modes
def classes_from_config(rep, config_path):
    """Config mode: load class labels and paths from a JSON file."""
    rep.info(f"Config file: {config_path}")

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)

    except (OSError, json.JSONDecodeError) as e:
        rep.fail(f"Could not read the config file: {e}")
        return None

    if not isinstance(data, dict) or not data:
        rep.fail(
            'Config must be a non-empty JSON object like '
            '{"class_0": "/path", "class_1": "/path"}'
        )
        return None

    classes = {}
    initial_failures = rep.counts["FAIL"]

    for label, p in data.items():
        if not isinstance(p, str) or not p.strip():
            rep.fail(f"Entry '{label}' has an invalid path value: {p!r}")
            continue

        classes[str(label)] = Path(p).expanduser()

    if rep.counts["FAIL"] > initial_failures:
        return None

    rep.ok(f"Config loaded: {len(classes)} class entries")
    return classes


def classes_from_root(rep, root):
    """Root mode: every sub-folder of the dataset root is a class."""
    root = root.resolve()

    rep.info(f"Dataset root given: {root}")

    effective, chain = resolve_root(root)

    if len(chain) > 1:
        rep.warn("Wrapper folder(s) detected (common in Kaggle zips). Chain:")

        for i, p in enumerate(chain):
            print(f"       {'  ' * i}{p.name}/")

        rep.info(f"Effective dataset root: {effective}")

    else:
        rep.ok("No wrapper nesting at the root")

    dirs, files, ignored = list_children(effective)

    root_images = [f for f in files if is_image(f)]
    root_other = [f for f in files if not is_image(f)]

    rep.info(
        f"{len(dirs)} folder(s), {len(root_images)} image(s), "
        f"{len(root_other)} other file(s), "
        f"{ignored} hidden/system entr(y/ies) ignored"
    )

    if root_other:
        rep.warn(
            "Non-image files at the root: "
            + ", ".join(f.name for f in root_other[:10])
        )

    if root_images:
        rep.warn(
            f"{len(root_images)} loose image(s) at the root "
            "next to class folders (unlabeled?)"
        )

    if not dirs:
        rep.fail(f"No class folders found at the root: {effective}")
        return None

    return {d.name: d for d in dirs}


# validation
def validate_classes(rep, classes):
    """Validate class folders and report dataset statistics."""
    rep.section("Class folders")

    results = {}

    print(
        f"  {'label':<16}{'folder':<26}"
        f"{'images':>8}{'nested':>8}{'other':>7}"
    )

    for label, given in classes.items():
        path = given.resolve()

        if not path.exists():
            rep.fail(f"[{label}] path does not exist: {path}")
            continue

        if not path.is_dir():
            rep.fail(f"[{label}] path is not a directory: {path}")
            continue

        resolved, chain = resolve_class_folder(path)
        stats = scan_folder(resolved)

        results[label] = {
            "path": path,
            "resolved": resolved,
            "stats": stats,
        }

        print(
            f"  {label:<16}{resolved.name:<26}"
            f"{stats['direct']:>8}{stats['nested']:>8}"
            f"{stats['other']:>7}"
        )

        if len(chain) > 1:
            rep.warn(
                f"[{label}] '{path.name}' has no images of its own, "
                f"only a sub-folder. Using inner folder: {resolved}"
            )

        if stats["direct"] + stats["nested"] == 0:
            rep.fail(f"[{label}] contains no images: {resolved}")

        if stats["subdirs"]:
            rep.warn(
                f"[{label}] contains sub-folders: {stats['subdirs']}"
            )

        if stats["other"]:
            rep.warn(
                f"[{label}] contains {stats['other']} non-image file(s)"
            )

    # cross-class checks
    rep.section("Cross-class checks")

    if len(classes) < MIN_CLASSES:
        rep.fail(
            f"Only {len(classes)} class(es) given; "
            f"at least {MIN_CLASSES} are required"
        )
    else:
        rep.ok(
            f"{len(classes)} classes given (minimum {MIN_CLASSES})"
        )

    labels = list(results)
    problems = False

    for i in range(len(labels)):
        for j in range(i + 1, len(labels)):
            label_a = labels[i]
            label_b = labels[j]

            folder_a = results[label_a]["resolved"]
            folder_b = results[label_b]["resolved"]

            if folder_a == folder_b:
                problems = True
                rep.fail(
                    f"[{label_a}] and [{label_b}] point to the "
                    f"same folder: {folder_a}"
                )

            elif (
                folder_a.is_relative_to(folder_b)
                or folder_b.is_relative_to(folder_a)
            ):
                problems = True
                rep.fail(
                    f"[{label_a}] and [{label_b}] overlap "
                    "(one folder is inside the other); "
                    "images would be counted twice"
                )

    if not problems:
        rep.ok(
            "No class folders are duplicated or nested inside each other"
        )

    # similar folder names
    seen = {}

    for label, result in results.items():
        folder_name = result["resolved"].name
        key = normalize(folder_name)

        seen.setdefault(key, []).append(
            f"{label}:{folder_name}"
        )

    for names in seen.values():
        if len(names) > 1:
            rep.warn(f"Folder names look alike: {names}")

    # summary
    rep.section("Summary")

    total_images = sum(
        result["stats"]["direct"] + result["stats"]["nested"]
        for result in results.values()
    )

    rep.info(f"Classes validated: {len(results)} of {len(classes)}")

    rep.info(
        f"Images counted (recursive, by extension only): {total_images}"
    )

    return results


# main discovery function
def discover(arg):
    rep = Reporter("discovery")

    rep.section("Input")

    target = Path(arg).expanduser()

    if target.is_file() and target.suffix.lower() == ".json":
        rep.info("Mode: config (classes listed in a JSON file)")
        classes = classes_from_config(rep, target)

    elif target.is_dir():
        rep.info("Mode: root (each sub-folder is a class)")
        classes = classes_from_root(rep, target)

    else:
        rep.fail(
            f"Not found, or not a .json file / folder: {target} "
            "(quote the path if it has spaces)"
        )
        rep.summary()
        return None, rep

    if not classes:
        rep.summary()
        return None, rep

    results = validate_classes(rep, classes)

    # prepare report data
    data = {
        label: {
            "folder": str(r["resolved"]),
            "images": (
                r["stats"]["direct"] + r["stats"]["nested"]
            ),
            "nested": r["stats"]["nested"],
            "other": r["stats"]["other"],
        }
        for label, r in results.items()
    }

    # save report for run_phase2.py
    save_report(
        rep,
        {label: r["resolved"] for label, r in results.items()},
        data,
    )

    rep.summary()

    return (results, rep) if not rep.counts["FAIL"] else (None, rep)


# execution
if __name__ == "__main__":
    arg = (
        sys.argv[1]
        if len(sys.argv) > 1
        else str(default_config_path())
    )

    results, reporter = discover(arg)

    sys.exit(reporter.exit_code())
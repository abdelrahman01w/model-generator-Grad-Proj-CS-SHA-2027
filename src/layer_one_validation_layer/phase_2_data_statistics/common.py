
import json
from datetime import datetime
from pathlib import Path


# Constants
VALIDATION_REPORT_NAME = "validation_report.json"


# Reporter
class Reporter:
    """Prints [INFO]/[PASS]/[WARN]/[FAIL] lines and keeps count of them."""

    def __init__(self, step_name):
        self.step_name = step_name
        self.messages = []
        self.counts = {"PASS": 0, "WARN": 0, "FAIL": 0}

    def _emit(self, level, msg):
        self.messages.append((level, msg))

        if level in self.counts:
            self.counts[level] += 1

        print(f"[{level}] {msg}")

    def info(self, msg):
        self._emit("INFO", msg)

    def ok(self, msg):
        self._emit("PASS", msg)

    def warn(self, msg):
        self._emit("WARN", msg)

    def fail(self, msg):
        self._emit("FAIL", msg)

    def section(self, title):
        print(f"\n=== {title} ===")

    def summary(self):
        c = self.counts
        print(
            f"\nResult ({self.step_name}): "
            f"{c['PASS']} PASS, "
            f"{c['WARN']} WARN, "
            f"{c['FAIL']} FAIL"
        )

    def exit_code(self):
        return 1 if self.counts["FAIL"] else 0

    def to_dict(self):
        return {
            "counts": self.counts,
            "messages": [
                {"level": level, "text": text}
                for level, text in self.messages
                if level != "INFO"
            ],
        }


# Small helpers
def pct(part, whole):
    return 0.0 if whole == 0 else 100.0 * part / whole


def print_table(headers, rows):
    """Print a plain-text table with aligned columns."""

    rows = [
        [
            str(value)
            if not isinstance(value, (int, float))
            else value
            for value in row
        ]
        for row in rows
    ]

    def cell(value):
        if isinstance(value, float):
            return f"{value:,.2f}"

        if isinstance(value, int):
            return f"{value:,}"

        return value

    text = [[cell(value) for value in row] for row in rows]

    widths = [len(str(header)) for header in headers]

    for row in text:
        for i, value in enumerate(row):
            widths[i] = max(widths[i], len(value))

    def fmt(values, raw=None):
        output = []

        for i, value in enumerate(values):
            numeric = (
                raw is not None
                and isinstance(raw[i], (int, float))
            )

            output.append(
                value.rjust(widths[i])
                if numeric
                else value.ljust(widths[i])
            )

        return "  " + "  ".join(output)

    print(fmt([str(header) for header in headers]))
    print("  " + "  ".join("-" * width for width in widths))

    for row_text, row_raw in zip(text, rows):
        print(fmt(row_text, row_raw))


# Locating project files
def find_assets_dir():
    """Find the assets folder relative to this file."""

    here = Path(__file__).resolve()

    for parent in here.parents:
        assets = parent / "assets"

        if assets.is_dir():
            return assets

    return Path.cwd() / "assets"


def default_config_path():
    """Return the path to the validation report."""
    return find_assets_dir() / "reports" / "validation_report.json"


# Loading classes
def load_classes(rep, arg=None):
    """
    Load validated image paths from validation_report.json.

    Expected structure:
        {
            "clean_dataset": {
                "class_1": ["/path/image1.jpeg", ...],
                "class_2": ["/path/image2.jpeg", ...]
            }
        }

    Returns:
        {label: [Path, ...]} or None if invalid.
    """
    target = Path(arg).expanduser() if arg else default_config_path()

    try:
        with open(target, "r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError) as error:
        rep.fail(f"Could not read validation report: {error}")
        return None

    if not isinstance(data, dict):
        rep.fail("Validation report must be a JSON object.")
        return None

    clean_dataset = data.get("clean_dataset")

    if not isinstance(clean_dataset, dict) or not clean_dataset:
        rep.fail("Validation report must contain a non-empty 'clean_dataset' object.")
        return None

    classes = {}

    for label, image_paths in sorted(clean_dataset.items()):
        if not isinstance(label, str) or not label.strip():
            rep.fail(f"Invalid class label: {label!r}")
            return None

        if not isinstance(image_paths, list) or not image_paths:
            rep.fail(f"[{label}] must contain a non-empty list of image paths.")
            return None

        paths = []

        for value in image_paths:
            if not isinstance(value, str) or not value.strip():
                rep.fail(f"[{label}] contains an invalid image path: {value!r}")
                return None

            path = Path(value).expanduser()

            if not path.is_file():
                rep.fail(f"[{label}] image file does not exist: {path}")
                return None

            paths.append(path.resolve())

        classes[label] = paths

    if len(classes) < 2:
        rep.fail("At least two classes are required.")
        return None

    rep.ok(
        f"Loaded {len(classes)} classes and "
        f"{sum(len(paths) for paths in classes.values())} images "
        f"from {target}"
    )

    return classes


# Saving reports
def save_report(rep, data):
    """
    Save this step's results as JSON in assets/reports/.

    Returns the report path, or None if saving fails.
    """

    reports_dir = find_assets_dir() / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    output_path = reports_dir / f"{rep.step_name}.json"

    payload = {
        "step": rep.step_name,
        "generated": datetime.now().isoformat(timespec="seconds"),
        "summary": rep.to_dict(),
        "data": data,
    }

    try:
        with open(output_path, "w", encoding="utf-8") as file:
            json.dump(payload, file, indent=4)

    except (OSError, TypeError, ValueError) as error:
        rep.fail(f"Could not save report: {error}")
        return None

    rep.info(f"Report saved to: {output_path}")

    return output_path


def load_report(step_name):
    """Read a saved step report, or return None if it does not exist."""

    path = find_assets_dir() / "reports" / f"{step_name}.json"

    if not path.is_file():
        return None

    try:
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)

    except (OSError, json.JSONDecodeError):
        return None


def images_by_class(source):
    """Load classes and return a dictionary of {class_name: [image_paths]} from a report file, directory, or dict."""
    from pathlib import Path
    import json
    
    # If it's already a dictionary, return it directly
    if isinstance(source, dict):
        return source

    path = Path(source)
    if path.is_file():
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for key in ["clean_dataset", "dataset", "classes"]:
            if key in data and isinstance(data[key], dict):
                return data[key]
        return data
    elif path.is_dir():
        result = {}
        for sub in sorted(path.iterdir()):
            if sub.is_dir():
                imgs = [str(p) for p in sub.iterdir() if p.is_file()]
                if imgs:
                    result[sub.name] = imgs
        return result
    return {}
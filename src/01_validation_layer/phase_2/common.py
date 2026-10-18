import json
import re
from datetime import datetime
from pathlib import Path

#constants
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tif", ".tiff", ".webp"}
IGNORED_NAMES = {".ds_store", "thumbs.db", "__macosx", "desktop.ini"}
CONFIG_NAME = "classes_config.json"
MAX_WRAPPER_DEPTH = 5
MIN_CLASSES = 2


#reporter
class Reporter:
    """Prints [INFO]/[PASS]/[WARN]/[FAIL] lines and keeps count of them."""

    def __init__(self, step_name):
        self.step_name = step_name
        self.messages = []  # (level, text)
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
        print(f"\nResult ({self.step_name}): {c['PASS']} PASS, {c['WARN']} WARN, {c['FAIL']} FAIL")

    def exit_code(self):
        return 1 if self.counts["FAIL"] else 0

    def to_dict(self):
        return {
            "counts": self.counts,
            "messages": [{"level": lv, "text": tx} for lv, tx in self.messages if lv != "INFO"],
        }


#small helpers
def is_image(path):
    return path.suffix.lower() in IMAGE_EXTS


def is_ignored(path):
    name = path.name.lower()
    return name.startswith(".") or name in IGNORED_NAMES


def normalize(name):
    return re.sub(r"[^a-z0-9]", "", name.lower())


def pct(part, whole):
    return 0.0 if whole == 0 else 100.0 * part / whole


def print_table(headers, rows):
    """Plain-text table. First column left-aligned, numeric columns right-aligned."""
    rows = [[str(c) if not isinstance(c, (int, float)) else c for c in r] for r in rows]

    def cell(v):
        if isinstance(v, float):
            return f"{v:,.2f}"
        if isinstance(v, int):
            return f"{v:,}"
        return v

    text = [[cell(v) for v in r] for r in rows]
    widths = [len(str(h)) for h in headers]
    for r in text:
        for i, v in enumerate(r):
            widths[i] = max(widths[i], len(v))

    def fmt(values, raw=None):
        out = []
        for i, v in enumerate(values):
            numeric = raw is not None and isinstance(raw[i], (int, float))
            out.append(v.rjust(widths[i]) if numeric else v.ljust(widths[i]))
        return "  " + "  ".join(out)

    print(fmt([str(h) for h in headers]))
    print("  " + "  ".join("-" * w for w in widths))
    for r_text, r_raw in zip(text, rows):
        print(fmt(r_text, r_raw))


#folder listing
def list_children(folder):
    """Return (subdirs, files, ignored_count) directly inside folder."""
    dirs, files, ignored = [], [], 0
    for p in sorted(folder.iterdir(), key=lambda x: x.name.lower()):
        if is_ignored(p):
            ignored += 1
        elif p.is_dir():
            dirs.append(p)
        elif p.is_file():
            files.append(p)
    return dirs, files, ignored


def walk_files(folder):
    """Every file under folder (recursive), skipping hidden/system entries. Sorted."""
    found = []
    for p in folder.rglob("*"):
        parts = p.relative_to(folder).parts
        if any(part.lower() in IGNORED_NAMES or part.startswith(".") for part in parts):
            continue
        if p.is_file():
            found.append(p)
    return sorted(found, key=lambda x: str(x).lower())


def resolve_root(root):
    """Root mode: descend through single-child wrapper folders (Kaggle zip nesting)."""
    chain = [root]
    current = root
    for _ in range(MAX_WRAPPER_DEPTH):
        dirs, files, _ = list_children(current)
        has_direct_images = any(is_image(f) for f in files)
        if len(dirs) == 1 and not has_direct_images:
            child_dirs, _, _ = list_children(dirs[0])
            if child_dirs:  # child has subfolders -> wrapper, not a class folder
                current = dirs[0]
                chain.append(current)
                continue
        break
    return current, chain


def resolve_class_folder(folder):
    """Class mode: no images + a single sub-folder means a wrapper (Healthy/Healthy/*.jpg)."""
    chain = [folder]
    current = folder
    for _ in range(MAX_WRAPPER_DEPTH):
        dirs, files, _ = list_children(current)
        if len(dirs) == 1 and not any(is_image(f) for f in files):
            current = dirs[0]
            chain.append(current)
            continue
        break
    return current, chain


#locating project files
def find_assets_dir():
    """Walk up from this file looking for an 'assets' folder (same one main.py writes to)."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "assets").is_dir():
            return parent / "assets"
    return Path.cwd() / "assets"


def default_config_path():
    return find_assets_dir() / CONFIG_NAME


#loading classes
def load_classes(rep, arg=None):
    """
    Returns {label: resolved_class_folder (Path)} or None if the input is unusable.

    arg can be a classes_config.json file (config mode), a dataset root folder
    (root mode: each sub-folder is a class), or None (use assets/classes_config.json).
    """
    target = Path(arg).expanduser() if arg else default_config_path()

    if target.is_file() and target.suffix.lower() == ".json":
        classes = _classes_from_config(rep, target)
    elif target.is_dir():
        classes = _classes_from_root(rep, target)
    else:
        rep.fail(f"Not found, or not a .json file / folder: {target} (quote the path if it has spaces)")
        return None

    if classes is None:
        return None
    if len(classes) < MIN_CLASSES:
        rep.fail(f"Only {len(classes)} class(es) found; at least {MIN_CLASSES} are required")
        return None
    return classes


def _classes_from_config(rep, config_path):
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        rep.fail(f"Could not read the config file: {e}")
        return None
    if not isinstance(data, dict) or not data:
        rep.fail('Config must be a non-empty JSON object like {"class_0": "/path", ...}')
        return None

    classes, bad = {}, False
    for label, p in data.items():
        if not isinstance(p, str) or not p.strip():
            rep.fail(f"[{label}] invalid path value: {p!r}")
            bad = True
            continue
        path = Path(p).expanduser().resolve()
        if not path.is_dir():
            rep.fail(f"[{label}] folder does not exist: {path}")
            bad = True
            continue
        resolved, chain = resolve_class_folder(path)
        if len(chain) > 1:
            rep.info(f"[{label}] using inner folder {resolved} (outer folder has no images of its own)")
        classes[str(label)] = resolved
    if bad:
        rep.fail("Fix the config first (run step1_discovery.py to see the details)")
        return None
    return classes


def _classes_from_root(rep, root):
    effective, chain = resolve_root(root.resolve())
    if len(chain) > 1:
        rep.info(f"Wrapper folder(s) skipped; dataset root is {effective}")
    dirs, _, _ = list_children(effective)
    if not dirs:
        rep.fail(f"No class folders found in {effective}")
        return None
    return {d.name: d for d in dirs}


def images_by_class(classes):
    """{label: [image Paths]} - recursive, by extension only."""
    return {label: [p for p in walk_files(folder) if is_image(p)] for label, folder in classes.items()}


#saving reports
def save_report(rep, classes, data):
    """
    Save this step's results as JSON in <assets>/reports/<step_name>.json so the final
    summary can read them. Refuses to write inside any class folder (data stays untouched).
    Returns the path, or None if it was not written.
    """
    reports_dir = (find_assets_dir() / "reports").resolve()
    for label, folder in classes.items():
        folder = folder.resolve()
        if reports_dir == folder or reports_dir.is_relative_to(folder):
            rep.fail(f"Refusing to save the report inside class folder [{label}]: {reports_dir}")
            return None
    reports_dir.mkdir(parents=True, exist_ok=True)
    out = reports_dir / f"{rep.step_name}.json"
    payload = {
        "step": rep.step_name,
        "generated": datetime.now().isoformat(timespec="seconds"),
        "summary": rep.to_dict(),
        "data": data,
    }
    with open(out, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=4)
    rep.info(f"Report saved to: {out}")
    return out


def load_report(step_name):
    """Read a saved step report, or None if it does not exist yet."""
    path = find_assets_dir() / "reports" / f"{step_name}.json"
    if not path.is_file():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
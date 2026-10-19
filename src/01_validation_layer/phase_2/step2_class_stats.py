import statistics
import sys

from common import (
    Reporter,
    load_classes,
    pct,
    print_table,
    save_report,
)


BALANCED_MAX = 1.5
MILD_MAX = 3.0

STEP_NAME = "class_stats"


# helpers
def verdict_for(ratio):
    if ratio < BALANCED_MAX:
        return "balanced"
    if ratio <= MILD_MAX:
        return "mild imbalance"
    return "significant imbalance"


# class counts
def report_class_counts(rep, classes):
    rep.section("Class counts")
    counts = {label: len(paths) for label, paths in classes.items()}
    total = sum(counts.values())

    if total == 0:
        rep.fail("No images found in any class")
        return {"counts": counts, "total": 0}

    rows = [[label, n, pct(n, total)] for label, n in counts.items()]
    rows.append(["TOTAL", total, 100.0])
    print_table(["label", "images", "percent"], rows)

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


# run
def run(arg=None):
    """Returns (data, reporter), or (None, reporter) if the input is unusable."""
    rep = Reporter(STEP_NAME)

    rep.section("Input")
    classes = load_classes(rep, arg)
    if classes is None:
        rep.summary()
        return None, rep

    data = {"class_stats": report_class_counts(rep, classes)}

    save_report(rep, data)
    rep.summary()
    return data, rep


if __name__ == "__main__":
    _, reporter = run(sys.argv[1] if len(sys.argv) > 1 else None)
    sys.exit(reporter.exit_code())
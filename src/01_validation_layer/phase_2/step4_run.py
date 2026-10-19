import json
import sys
import traceback
from collections import defaultdict
from datetime import datetime

from common import Reporter, default_config_path, find_assets_dir, load_classes

import step1_discovery
import step2_class_stats
import step3_dimensions


PHASE2_REPORT_NAME = "phase2_report.json"   # written beside validation_report.json


# running one step
def run_step(title, function, arg):
    """Run one step and return (data, reporter).
    If the step crashes, we still return a reporter with a FAIL message,
    so one broken step does not hide the results of the others."""
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)

    try:
        data, reporter = function(arg)
    except Exception:
        traceback.print_exc()          # show the full error for debugging
        data = None
        reporter = Reporter(title)
        reporter.fail("The step crashed (see the error above)")

    return data, reporter


# output for the next step
def phase2_report_path():
    """Where the Phase 2 dataset file is written (next to validation_report.json)."""
    return find_assets_dir() / "reports" / PHASE2_REPORT_NAME


def write_phase2_dataset(source, unreadable):
    """Write a file in the same format as validation_report.json:
        {"clean_dataset": {"class_0": ["/path/a.jpeg", ...], ...}}
    It lists every image from the input report except the ones Step 3
    could not open, so the next step can load it with load_classes().

    unreadable = {label: [path, ...]} as returned by Step 3.
    Returns a Reporter."""
    rep = Reporter("phase2_dataset")

    classes = load_classes(rep, source)
    if classes is None:
        return rep

    bad = {path for paths in unreadable.values() for path in paths}

    clean = defaultdict(list)
    for label, paths in classes.items():
        for path in paths:
            if str(path) not in bad:
                clean[label].append(str(path))

                
    lost = [label for label in classes if label not in clean]
    if lost:
        rep.fail(f"Class(es) lost all their images (all unreadable): {', '.join(lost)}")

    payload = {
        "generated": datetime.now().isoformat(timespec="seconds"),
        "source": str(source),
        "excluded_unreadable": sorted(bad),
        "clean_dataset": dict(sorted(clean.items())),
    }

    output = phase2_report_path()
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        with open(output, "w", encoding="utf-8") as file:
            json.dump(payload, file, indent=4)
    except (OSError, TypeError, ValueError) as error:
        rep.fail(f"Could not save the Phase 2 dataset: {error}")
        return rep

    total = sum(len(paths) for paths in clean.values())
    rep.ok(f"Phase 2 dataset saved: {output} ({total:,} images, {len(bad)} excluded)")
    return rep


#final summary
def print_final_summary(results):
    """results = list of (title, reporter). Prints every PASS/WARN/FAIL message."""
    totals = {"PASS": 0, "WARN": 0, "FAIL": 0}

    print("\n" + "#" * 70)
    print("PHASE 2 - FINAL SUMMARY")
    print("#" * 70)

    for title, reporter in results:
        counts = reporter.counts
        print(f"\n{title}  ({counts['PASS']} PASS, {counts['WARN']} WARN, {counts['FAIL']} FAIL)")

        for level, text in reporter.messages:
            if level == "INFO":
                continue                # INFO lines are details, not results
            print(f"  [{level}] {text}")

        for level in totals:
            totals[level] += counts[level]

    print("\n" + "-" * 70)
    print(f"TOTAL: {totals['PASS']} PASS, {totals['WARN']} WARN, {totals['FAIL']} FAIL")

    if totals["FAIL"] > 0:
        print("PHASE 2 RESULT: FAILED (fix the FAIL messages above)")
    elif totals["WARN"] > 0:
        print("PHASE 2 RESULT: PASSED WITH WARNINGS (review the WARN messages above)")
    else:
        print("PHASE 2 RESULT: PASSED")

    return totals["FAIL"]


#main
def run_all(report_path=None):
    """Run every Phase 2 step on validation_report.json and print the final summary.
    report_path: the report written by Phase 1 (default: assets/reports/validation_report.json).
    Returns the number of FAIL messages (0 = no failures).
    It never calls sys.exit(), so another script (like __main__.py) can call it safely."""
    report_path = str(report_path) if report_path else str(default_config_path())
    results = []

    # Step 1: input check. It acts as a gate: if it reports failures, the later
    # steps would run on a broken input, so we skip them.
    data, reporter = run_step("STEP 1 - Input check", step1_discovery.discover, report_path)
    results.append(("Step 1 - Input check", reporter))

    if data is None:
        print("\nStopping: Step 1 reported failures, so the other steps are skipped. "
              "Fix them and run again.")
    else:
        # Step 2: class counts
        _, reporter = run_step("STEP 2 - Class statistics", step2_class_stats.run, report_path)
        results.append(("Step 2 - Class statistics", reporter))

        # Step 3: image dimensions
        dimensions, reporter = run_step("STEP 3 - Image dimensions", step3_dimensions.run, report_path)
        results.append(("Step 3 - Image dimensions", reporter))

        # Output: clean_dataset file for the next step (needs Step 3's unreadable list)
        if dimensions is not None:
            _, reporter = run_step(
                "OUTPUT - Phase 2 dataset",
                lambda path: (None, write_phase2_dataset(path, dimensions["unreadable"])),
                report_path,
            )
            results.append(("Output - Phase 2 dataset", reporter))
        else:
            print("\nPhase 2 dataset not written: Step 3 did not produce results.")

    return print_final_summary(results)


def main():
    """Command-line entry point: python step4_run.py [validation_report.json]"""
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    failures = run_all(arg)
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
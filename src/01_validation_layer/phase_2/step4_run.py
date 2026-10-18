import sys
import traceback

from common import Reporter, default_config_path

import step1_discovery
import step2_class_stats
import step3_dimensions


# running one step
def run_discovery(arg):
    """Step 1 needs a path, so use the default config when none is given."""
    target = arg if arg else str(default_config_path())
    return step1_discovery.discover(target)


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
def run_all(arg=None):
    """Run every Phase step and print the final summary.
    Returns the number of FAIL messages (0 = no failures).
    It never calls sys.exit(), so another script (like main.py) can call it safely."""
    results = []

    # Step 1: folder discovery. It acts as a gate: if it reports failures, the later
    # steps would run on a broken dataset, so we skip them.
    data, reporter = run_step("STEP 1 - Folder discovery", run_discovery, arg)
    results.append(("Step 1 - Folder discovery", reporter))

    if data is None:
        print("\nStopping: Step 1 reported failures, so the other steps are skipped. "
              "Fix them and run again.")
    else:
        # Step 2: file inventory + class counts
        _, reporter = run_step("STEP 2 - File inventory and class statistics",
                               step2_class_stats.run, arg)
        results.append(("Step 2 - File inventory and class statistics", reporter))

        # Step 3: image dimensions
        _, reporter = run_step("STEP 3 - Image dimensions", step3_dimensions.run, arg)
        results.append(("Step 3 - Image dimensions", reporter))

    return print_final_summary(results)


def main():
    """Command-line entry point: python step4_run.py [config_or_folder]"""
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    failures = run_all(arg)
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
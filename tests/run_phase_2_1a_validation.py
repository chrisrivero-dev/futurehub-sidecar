import json
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ai.missing_info_detector import detect_missing_information

FIXTURE_PATH = "tests/phase_2_1a_missing_info_fixtures.json"


def run():
    with open(FIXTURE_PATH, "r") as f:
        fixtures = json.load(f)

    failures = 0
    skipped = 0

    for case in fixtures:
        # --------------------------------------------------
        # TODO (Phase 2.2):
        # Re-enable cases that rely on text-based inference.
        #
        # Phase 2.1a is metadata-only observation.
        # If metadata is empty, inference is out of scope.
        # --------------------------------------------------
        if not case["input"].get("metadata"):
            skipped += 1
            continue

        result = detect_missing_information(
            messages=case["input"]["messages"],
            intent=case["input"]["intent"],
            mode=case["input"]["mode"],
            metadata=case["input"]["metadata"],
        )

        blocking = sorted(
            item["key"]
            for item in result.get("items", [])
            if item["severity"] == "blocking"
        )
        non_blocking = sorted(
            item["key"]
            for item in result.get("items", [])
            if item["severity"] == "non_blocking"
        )

        if (
            blocking != sorted(case["expected"]["blocking_keys"])
            or non_blocking != sorted(case["expected"]["non_blocking_keys"])
        ):
            failures += 1
            print(f"\n❌ FAIL: {case['name']}")
            print("Expected blocking:", case["expected"]["blocking_keys"])
            print("Got blocking     :", blocking)
            print("Expected non-blocking:", case["expected"]["non_blocking_keys"])
            print("Got non-blocking     :", non_blocking)
            print("DEBUG intent input  :", case["input"].get("intent"))
            print("DEBUG metadata input:", case["input"].get("metadata"))
            print("DEBUG messages input:", case["input"].get("messages"))
            print("DEBUG detector output:", result)
            print("-" * 60)

    if failures:
        raise SystemExit(f"\n❌ {failures} validation failures ({skipped} skipped — Phase 2.2)")
    else:
        print(f"\n✅ Phase 2.1a validation passed ({skipped} skipped — Phase 2.2)")


if __name__ == "__main__":
    run()

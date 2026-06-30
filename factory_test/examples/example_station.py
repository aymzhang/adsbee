#!/usr/bin/env python3
"""EXAMPLE factory test station — reference only.

Shows how the example phases get assembled into a Test, wired to output
callbacks (local JSON + the central-upload placeholder), and run in an operator
loop. Developers should write their own station from scratch using this as a
template.

    pip install -r requirements.txt
    python example_station.py        # Ctrl-C to stop the station

Headless / unattended: replace `test_start` with a fixed id, e.g.
    test.execute(test_start=lambda: "DUT-DEV-0001")
"""

import logging
import os
from pathlib import Path

import openhtf as htf
from openhtf.output.callbacks import json_factory
from openhtf.plugs import user_input

import example_phases as phases
from example_callbacks import UploadToCentral

BASE_DIR = Path(__file__).parent
RESULTS_DIR = BASE_DIR / "results"


def build_test() -> htf.Test:
    test = htf.Test(
        *phases.ALL_PHASES,
        test_name="EXAMPLE Factory Test (OpenHTF reference)",
    )
    test.add_output_callbacks(
        # Per-DUT JSON record on the local disk.
        # Prefix example results with example_ so they're never confused with
        # real production results.
        json_factory.OutputToJSON(
            str(RESULTS_DIR / "example_{dut_id}_{start_time_millis}.json"), indent=2
        ),
        # Ship the same record to a central location (placeholder for now).
        UploadToCentral(endpoint=None),
    )
    return test


def main():
    logging.basicConfig(level=logging.INFO)
    os.makedirs(RESULTS_DIR, exist_ok=True)
    test = build_test()
    try:
        while True:
            test.execute(
                test_start=user_input.prompt_for_test_start(
                    message="Scan or type DUT serial, then press ENTER:"
                )
            )
    except KeyboardInterrupt:
        logging.info("Station stopped.")


if __name__ == "__main__":
    main()

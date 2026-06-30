#!/usr/bin/env python3
"""EXAMPLE OpenHTF station driven by the live web GUI (reference only).

Same test as example_station.py, but served through OpenHTF's built-in
StationServer dashboard (default http://localhost:4444); phase/measurement state
streams in live.

IMPORTANT LIMITATION: the bundled web GUI in this OpenHTF version is
MONITOR-ONLY. It displays live state and history but has no way to ANSWER
prompts, so a console `prompt_for_test_start()` would hang in trigger_phase
forever from the browser. This example therefore triggers each unit with an
auto-generated serial (see `_auto_dut_id`). A real station should trigger from a
barcode-scanner plug, or answer prompts in the console.

Separation of concerns (what you asked for):
  * This station only RUNS tests and PRODUCES records — the JSON files written by
    build_test()'s callbacks (examples/results/example_*.json) plus the
    UploadToCentral placeholder.
  * ANALYSIS is a separate step. The web GUI is for running, not analytics; crunch
    the records with example_analyze.py (or a real pipeline pointed at your
    central store).

    pip install -r requirements.txt
    python examples/example_station_web.py     # then open http://localhost:4444
"""

import itertools
import logging
import os
import time

from openhtf.output.servers.station_server import StationServer
from openhtf.output.web_gui import web_launcher
from openhtf.util import configuration

# Reuse the exact same Test definition as the console station.
from example_station import build_test, RESULTS_DIR

CONF = configuration.CONF
# StationServer's default port is 0 (a RANDOM free port). Pin it so the
# dashboard is always at the same address for operators. Set to 0 to auto-pick.
WEB_GUI_PORT = 4444

# Non-blocking trigger: the bundled GUI can't answer prompts (see module
# docstring), so auto-generate a serial per unit instead of prompting.
_serial_counter = itertools.count(1)


def _auto_dut_id() -> str:
    return f"DUT-AUTO-{next(_serial_counter):04d}"


def main():
    logging.basicConfig(level=logging.INFO)
    os.makedirs(RESULTS_DIR, exist_ok=True)
    CONF.load(station_server_port=WEB_GUI_PORT)
    # StationServer hosts the dashboard for the duration of the `with` block.
    with StationServer() as server:
        # Launch the browser at the ACTUAL bound port so the URL always matches,
        # even if you set WEB_GUI_PORT = 0 to auto-pick.
        web_launcher.launch(f"http://localhost:{server.port}")
        try:
            while True:
                test = build_test()
                # Feed live/final state to the dashboard. The JSON + upload
                # callbacks from build_test() still run, so records are produced
                # for the separate analysis step regardless of the GUI.
                test.add_output_callbacks(server.publish_final_state)
                test.execute(test_start=_auto_dut_id)  # non-blocking; see note above
                time.sleep(2)  # pace units so the live dashboard is watchable
        except KeyboardInterrupt:
            logging.info("Station stopped.")


if __name__ == "__main__":
    main()

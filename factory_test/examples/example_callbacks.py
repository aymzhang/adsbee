"""EXAMPLE output callbacks — reference only.

OpenHTF calls each registered output callback once per test with the immutable
`test_record` (DUT id, outcome, every measurement + its limit + pass/fail,
timing, logs, attachments). Built-in callbacks write JSON locally; this
placeholder shows how you'd ship the same record to a central location.
"""

import json
import logging

_LOG = logging.getLogger(__name__)


class UploadToCentral:
    """PLACEHOLDER: push a finished TestRecord to a central store for analysis.

    Swap the body for a real POST / DB insert / cloud upload. Kept side-effect
    free (just prints) so the examples are self-contained.
    """

    def __init__(self, endpoint: str | None = None):
        self.endpoint = endpoint

    def __call__(self, test_record):
        payload = _summarize(test_record)
        _LOG.info(
            "Would upload DUT %s (outcome=%s) to %s",
            payload["dut_id"],
            payload["outcome"],
            self.endpoint or "<unset endpoint>",
        )
        # TODO: ship it, e.g.:
        #   import requests
        #   requests.post(self.endpoint, json=payload, timeout=10).raise_for_status()
        print(json.dumps(payload, indent=2, default=str))


def _summarize(test_record) -> dict:
    """Flatten the parts of a TestRecord most analyses care about."""
    measurements = {}
    for phase in test_record.phases:
        for name, meas in phase.measurements.items():
            # Guarded: dimensioned/unset measurements expose .value differently,
            # so never let summarization crash the upload.
            try:
                value = meas.measured_value.value if meas.measured_value.is_value_set else None
            except Exception:
                value = None
            measurements[name] = {"value": value, "outcome": meas.outcome.name}
    return {
        "dut_id": test_record.dut_id,
        "outcome": test_record.outcome.name,  # PASS / FAIL / ERROR / TIMEOUT / ABORTED
        "start_time_millis": test_record.start_time_millis,
        "end_time_millis": test_record.end_time_millis,
        "measurements": measurements,
    }

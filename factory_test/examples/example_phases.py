"""EXAMPLE test phases — a reference cookbook, not a finished test.

Roll your own phases module using these as a guide. Each phase is a plain
function: `test` first, then any plugs it declares, by name.

  * BASIC examples    — the everyday declare-measurement-with-a-range pattern.
  * ADVANCED examples — the less-obvious OpenHTF features you'll eventually
                        want: regex/custom validators, swept (dimensioned)
                        measurements, attachments, and phase options
                        (timeouts, bounded retries).
"""

import json

import openhtf as htf
from openhtf.util import units

from example_plugs import FixturePlug, InstrumentPlug

FIRMWARE_IMAGE_PATH = "build/firmware.bin"  # TODO: point at your build artifact.


# ─────────────────────────── BASIC examples ────────────────────────────────

@htf.plug(fixture=FixturePlug)
@htf.measures(
    htf.Measurement("flash_duration_s").with_units(units.SECOND).in_range(0, 120)
)
def flash_firmware(test, fixture):
    """Flash firmware and record how long it took."""
    test.logger.info("=== Flashing firmware ===")
    test.measurements.flash_duration_s = fixture.flash_image(FIRMWARE_IMAGE_PATH)
    return htf.PhaseResult.CONTINUE


@htf.plug(fixture=FixturePlug)
def actuate_fixture(test, fixture):
    """A phase with NO measurements — pure side effects (actuation/setup)."""
    test.logger.info("=== Actuating fixture ===")
    fixture.actuate("apply_power")
    fixture.actuate("press_boot_button")
    return htf.PhaseResult.CONTINUE


@htf.plug(instrument=InstrumentPlug)
@htf.measures(
    htf.Measurement("supply_voltage").with_units(units.VOLT).in_range(3.2, 3.4),
    htf.Measurement("supply_current").with_units(units.AMPERE).in_range(0.05, 0.5),
)
def measure_power(test, instrument):
    """Two range-validated measurements — the bread-and-butter pattern."""
    test.logger.info("=== Measuring power rails ===")
    test.measurements.supply_voltage = instrument.read_supply_voltage()
    test.measurements.supply_current = instrument.read_supply_current()
    return htf.PhaseResult.CONTINUE


# ───────────────────────── ADVANCED examples ───────────────────────────────

def _is_power_of_two(value: int) -> bool:
    """Custom validator: True if `value` is a positive power of two.

    A validator is just a callable returning truthy/falsy. Define it BEFORE the
    phase that references it — the decorator runs at import time.
    """
    v = int(value)
    return v > 0 and (v & (v - 1)) == 0


@htf.plug(instrument=InstrumentPlug)
@htf.measures(
    # Validate a STRING by regex instead of a numeric range (e.g. a build hash
    # that must be 7-40 hex chars).
    htf.Measurement("firmware_git_hash").matches_regex(r"^[0-9a-f]{7,40}$"),
    # Validate with an ARBITRARY predicate — anything range/regex can't express.
    htf.Measurement("calibration_code").with_validator(_is_power_of_two),
)
def verify_identity(test, instrument):
    """Validation beyond ranges: regex match and a custom predicate."""
    test.logger.info("=== Verifying identity ===")
    test.measurements.firmware_git_hash = instrument.read_firmware_git_hash()
    test.measurements.calibration_code = instrument.read_calibration_code()
    return htf.PhaseResult.CONTINUE


SWEEP_FREQS_HZ = (1_089_000_000, 1_090_000_000, 1_091_000_000)


def _every_point_in_range(minimum, maximum):
    """Validator for a DIMENSIONED measurement.

    Gotcha: OpenHTF hands a dimensioned measurement's validator the ENTIRE list
    of points (each is `[coord, ..., measured_value]`), NOT one point at a time.
    So `.in_range(...)` does NOT work on a sweep — you iterate the points
    yourself, as here.
    """
    def validate(points):
        return all(minimum <= p[-1] <= maximum for p in points)
    return validate


@htf.plug(instrument=InstrumentPlug)
@htf.measures(
    # A DIMENSIONED (swept) measurement: ONE measurement holding many points,
    # indexed here by frequency. See _every_point_in_range for why a custom
    # validator is required instead of .in_range().
    htf.Measurement("rf_power_sweep")
    .with_dimensions(units.HERTZ)
    .with_validator(_every_point_in_range(18, 22))
)
def sweep_rf_power(test, instrument):
    """Sweep power vs. frequency, and attach the raw data to the record."""
    test.logger.info("=== Sweeping RF power ===")
    raw = {}
    for freq in SWEEP_FREQS_HZ:
        power = instrument.read_power_at(freq)
        # Dimensioned measurements use INDEXED assignment, not plain `= value`.
        test.measurements.rf_power_sweep[freq] = power
        raw[str(freq)] = power
    # ATTACHMENTS: stash arbitrary artifacts (raw captures, logs, plots) in the
    # record alongside the measurements. Data must be bytes.
    test.attach(
        "rf_power_sweep_raw", json.dumps(raw).encode(), mimetype="application/json"
    )
    return htf.PhaseResult.CONTINUE


@htf.PhaseOptions(timeout_s=60, repeat_limit=3)
@htf.plug(fixture=FixturePlug)
def flash_with_retry(test, fixture):
    """PHASE OPTIONS + control flow: a bounded retry with a timeout.

    `repeat_limit=3` caps attempts; returning `PhaseResult.REPEAT` re-runs the
    phase; `timeout_s` fails it if it hangs. Ideal for flaky steps like flashing.
    """
    test.logger.info("=== Flashing (with retry) ===")
    if fixture.try_flash_image(FIRMWARE_IMAGE_PATH):
        return htf.PhaseResult.CONTINUE
    test.logger.warning("Flash failed — repeating.")
    return htf.PhaseResult.REPEAT


# The ordered phase list the station runs. Order == execution order.
ALL_PHASES = (
    # basic
    flash_firmware,
    actuate_fixture,
    measure_power,
    # advanced
    verify_identity,
    sweep_rf_power,
    flash_with_retry,
)

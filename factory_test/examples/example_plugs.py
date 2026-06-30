"""EXAMPLE hardware abstraction layer (OpenHTF *plugs*) — reference only.

Copy the pattern into your own plugs module; don't import this in production.

A "plug" is OpenHTF's unit of reusable hardware/resource access. Phases declare
the plugs they need with `@htf.plug(...)`; OpenHTF builds ONE instance per test,
shares it across every phase, and calls `.tearDown()` automatically at the end.
Because the instance is shared for the whole test, a plug is also where per-DUT
state lives (see the retry counter below).

All I/O here is SIMULATED so the examples run without hardware. Replace each
method body with real instrument / fixture access (pyvisa, serial, GPIO, a
flashing CLI subprocess, etc.).
"""

import random
import time

from openhtf.core.base_plugs import BasePlug


class FixturePlug(BasePlug):
    """Controls the fixture: power, flashing, actuators."""

    def __init__(self):
        super().__init__()
        # NOTE: BasePlug injects self.logger automatically — never assign it here.
        # State on the plug persists across all phases of ONE test; the retry
        # example uses this to count attempts.
        self._flash_attempts = 0
        # TODO: open the connection to the fixture controller here.

    def flash_image(self, image_path: str) -> float:
        """Flash a firmware image to the DUT. Returns elapsed seconds."""
        self.logger.info("Flashing image: %s", image_path)
        t0 = time.monotonic()
        time.sleep(0.2)  # TODO: real flash (subprocess, UF2 copy, ...)
        return time.monotonic() - t0

    def try_flash_image(self, image_path: str) -> bool:
        """Flash that may transiently fail — drives the retry example.

        Simulates failing the first attempt then succeeding, so the retry phase
        deterministically REPEATs exactly once.
        """
        self._flash_attempts += 1
        ok = self._flash_attempts >= 2
        self.logger.info(
            "Flash attempt %d -> %s", self._flash_attempts, "ok" if ok else "FAILED"
        )
        return ok

    def actuate(self, name: str) -> None:
        self.logger.info("Actuating: %s", name)
        time.sleep(0.1)  # TODO: drive real actuator; ideally confirm position.

    def tearDown(self):
        self.logger.info("Releasing fixture (power down, home actuators).")
        # TODO: power down DUT, retract actuators, close handles.


class InstrumentPlug(BasePlug):
    """Reads measurements from bench instruments."""

    def __init__(self):
        super().__init__()
        # NOTE: BasePlug injects self.logger automatically — never assign it here.
        # TODO: open instrument sessions (pyvisa, sockets, ...).

    def read_supply_voltage(self) -> float:
        return random.uniform(3.25, 3.35)  # TODO: real DMM read

    def read_supply_current(self) -> float:
        return random.uniform(0.10, 0.30)  # TODO

    def read_center_frequency(self) -> float:
        return random.uniform(1_089_990_000, 1_090_010_000)  # TODO (Hz)

    def read_rf_power_dbm(self) -> float:
        return random.uniform(19.0, 21.0)  # TODO (dBm)

    def read_power_at(self, freq_hz: float) -> float:
        """Power (dBm) at one frequency — used by the sweep example."""
        return random.uniform(19.0, 21.0)  # TODO: tune to freq_hz, then read

    def read_calibration_code(self) -> int:
        return 64  # TODO: read code from DUT

    def read_firmware_git_hash(self) -> str:
        return "a1b2c3d"  # TODO: query DUT firmware build id

    def tearDown(self):
        self.logger.info("Closing instrument sessions.")
        # TODO: close sessions.

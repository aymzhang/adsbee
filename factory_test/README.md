# factory_test

Home for the production factory-fixture test code (flash → actuate → measure →
report). Real station code goes at this top level; runnable **OpenHTF reference
examples** live in [`examples/`](examples/).

## `examples/` — OpenHTF reference, not a framework

A minimal, runnable set of [OpenHTF](https://github.com/google/openhtf) examples
to evaluate whether OpenHTF is the right foundation, and to serve as a cookbook.

> **These are examples, not a framework to extend.** Read them, then **write your
> own station / phases / plugs from scratch**, copying the patterns you need.
> Everything hardware-facing is a placeholder returning simulated values, so the
> whole flow runs today with no hardware. Result files are written to
> `examples/results/` and **prefixed `example_`** so they're never confused with
> real production results.

### What the examples demonstrate

- **Phases** — ordered test steps, including a measurement-less actuation phase.
- **Measurement validation** — declarative limits/units (pass/fail recorded
  automatically), plus **regex** (`.matches_regex`) and **custom**
  (`.with_validator`) validators.
- **Dimensioned (swept) measurements** — one measurement holding many points,
  with the non-obvious validation gotcha (see below).
- **Attachments** — stashing raw artifacts (captures/logs) in the test record.
- **Phase options** — timeouts and bounded retries (`PhaseResult.REPEAT`).
- **Plugs** — reusable hardware access with automatic teardown and per-DUT state.
- **Output** — a per-DUT JSON record on disk **plus** a placeholder callback that
  would ship the same record to a central location.

## Setup (Poetry)

Dependencies are managed with [Poetry](https://python-poetry.org/). The env is
created in-project at `./.venv` (configured in `poetry.toml`):

```bash
cd factory_test
poetry install            # creates ./.venv and installs the locked deps
```

Then run commands with `poetry run …` (or `poetry shell` to activate the env).

**Console station** (prompts in the terminal):
```bash
poetry run python examples/example_station.py     # scan/type a serial; Ctrl-C to stop
```

**Web-GUI station** (live dashboard; auto-triggers units — see its docstring):
```bash
poetry run python examples/example_station_web.py # dashboard at http://localhost:4444
```

Both write an `example_…json` record to `examples/results/` per unit. For a
headless run of the console station, see the comment in
`examples/example_station.py` (`test_start=lambda: "DUT-DEV-0001"`).

## Running vs. analysis (kept separate)

The stations only **run tests and produce records**. **Analysis is a separate
step** — the web GUI is for live operation, not analytics. Crunch the records
with:
```bash
poetry run python examples/example_analyze.py     # yield + per-measurement stats over examples/results/
```
In production, point an analysis pipeline (DB + Grafana/Metabase, or your own)
at your **central store** instead of the local folder — fed by the
`UploadToCentral` callback in `example_callbacks.py`.

## Files

| File | Role |
|---|---|
| `examples/example_station.py` | Console station: builds the `Test`, registers callbacks, runs the operator loop. |
| `examples/example_station_web.py` | Same test served through the live web dashboard (http://localhost:4444). |
| `examples/example_phases.py` | The test steps — basic + advanced patterns, heavily commented. |
| `examples/example_plugs.py` | `FixturePlug` / `InstrumentPlug` hardware abstraction (placeholder I/O). |
| `examples/example_callbacks.py` | `UploadToCentral` output callback (placeholder for the central store). |
| `examples/example_analyze.py` | **Separate** analysis: reads records, prints yield + per-measurement stats. |
| `pyproject.toml` / `poetry.lock` | Poetry dependency spec + lockfile (`openhtf`). |

### Deploying to a fixture PC

The whole point of `poetry.lock` is reproducibility — `poetry install` on the
fixture PC installs the exact locked versions. If a fixture PC has only `pip`
(no Poetry), export a pip-installable lock instead:

```bash
poetry self add poetry-plugin-export        # one-time, Poetry 2.x unbundled export
poetry export -f requirements.txt -o requirements.txt --without-hashes
```

## Where the real work goes (search for `TODO`)

1. **`examples/example_plugs.py`** — replace each simulated read / flash /
   actuate with real instrument and fixture I/O. This is the bulk of the effort
   and is the same whether or not you keep OpenHTF.
2. **`examples/example_phases.py`** — set `FIRMWARE_IMAGE_PATH`, tighten limits.
3. **`examples/example_callbacks.py`** — implement the POST/DB insert to your
   central store.

## Gotchas worth knowing (learned the hard way)

- **Don't set `self.logger` in a plug `__init__`** — `BasePlug` injects it and
  raises if you assign it.
- **`.in_range()` does NOT work on a dimensioned measurement.** OpenHTF hands a
  dimensioned validator the *entire list* of points, not one at a time, so a
  range check raises `must be real number, not list`. Use a custom validator
  that iterates the points — see `_every_point_in_range` in
  `examples/example_phases.py`.
- **OpenHTF reads phase source code** for its descriptors, so phases must live in
  real `.py` files (not defined inside a function or `exec`'d).

## Trying out the validation

Tighten a limit in `examples/example_phases.py` (e.g. `supply_voltage …
in_range(3.35, 3.4)`) and rerun — the measurement, its phase, and the overall
test flip to FAIL automatically, captured in the JSON record. That auto-recorded
pass/fail with per-unit traceability is the main thing OpenHTF gives you over a
custom script.

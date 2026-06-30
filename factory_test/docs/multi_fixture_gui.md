# Decision: OpenHTF frontend communication & multi-fixture GUI (PyQt vs. web)

**Status:** analysis / recommendation for team review
**Scope:** how to drive multiple physical test fixtures in parallel, with an
operator UI, on top of OpenHTF.
**Basis:** verified against the installed `openhtf` **1.6.1** source in
`factory_test/.venv` (file paths cited below are under
`.venv/lib/python3.12/site-packages/openhtf/`).

---

## 1. How OpenHTF communicates with the web UI

- **Transport: SockJS over Tornado** (WebSocket with HTTP long-poll fallbacks).
  The pub/sub base class is `pub_sub.PubSub(sockjs.tornado.SockJSConnection)`.
  - `output/servers/pub_sub.py`
- **Live state is *pushed* one-directionally (server → browser).** A background
  `StationWatcher` thread tracks the currently-executing test; on every framework
  `notify_update()` (phase/measurement/plug/log change) it serializes the test
  state (`test_state.asdict_with_event()` → `data.convert_to_base_types`) and
  publishes it to all subscribers. Finished records (history) are served over
  plain HTTP handlers.
  - `output/servers/station_server.py`
- **There is no reverse channel for operator input.** `station_server.py` has
  *zero* prompt-handling code and no endpoint to answer a prompt. This is why
  `prompt_for_test_start()` cannot be answered in the browser and the test hangs
  in `trigger_phase` — **the bundled web GUI is monitor-only.**
- **Multi-station = multiple processes + a directory page.** Each fixture process
  runs its *own* `StationServer` and announces itself via **multicast**; a
  separate `DashboardServer` discovers them and serves a **list of stations**
  (clicking one opens that station's individual monitor view). It is not a
  unified control panel.
  - `output/servers/dashboard_server.py` (uses `openhtf/util/multicast.py`)

## 2. The hard constraint: one test per process

`Test.execute()` raises `InvalidTestStateError('Test already running')` if a test
is already executing in that process.

- `core/test_descriptor.py`

**Implication:** a single OpenHTF process runs **one fixture's tests
sequentially**. Driving N fixtures in parallel therefore requires **N OS
processes regardless of which UI you pick.** Some orchestration layer
(spawn/own/monitor N workers) is unavoidable either way — the GUI choice only
decides *what sits on top of it.*

## 3. Options

### Option A — OpenHTF web: `StationServer`-per-fixture + `DashboardServer`

```
DashboardServer (multicast discovery)
 ├─ StationServer 1  ← fixture process 1
 ├─ StationServer 2  ← fixture process 2
 └─ StationServer N  ← fixture process N
```

| Pros | Cons |
|---|---|
| Least new code; all built-in | **Monitor-only** — no in-browser operator input (serials/prompts/start-stop) |
| Browser-accessible from any machine | Multi-fixture view is just a **station list**, not one console |
| Live state + history for free | Frontend is an **older, low-maintenance Angular app** |

Workable only if monitoring suffices and serials/prompts come from a **barcode
scanner or the console**, not the browser.

### Option B — PyQt console + one OpenHTF worker subprocess per fixture

```
PyQt main process (operator console)
 ├─ Fixture panel 1 ──IPC──> OpenHTF worker proc 1
 ├─ Fixture panel 2 ──IPC──> OpenHTF worker proc 2
 └─ Fixture panel N ──IPC──> OpenHTF worker proc N
        operator input flows DOWN; live state + records flow UP
```

| Pros | Cons |
|---|---|
| **Real operator input** (serial entry, start/stop, prompt answers) | Custom UI work (Qt widgets, event wiring) |
| **One native window, N fixture panels** — true parallel console | You own the IPC + orchestration layer |
| Per-process **fault isolation** (one fixture crash ≠ all down) | Desktop-only (not browser-accessible) |
| Full styling/UX control for the operator | — |

OpenHTF still does all the real work in each worker (phases, measurement
validation, record generation); Qt replaces only the **frontend + orchestration**.

## 4. Recommendation

**Build the PyQt console (Option B).** Two reasons compound:

1. **Parallel fixtures force multi-process orchestration anyway** — that layer
   exists no matter what, so it isn't "extra" work attributable to PyQt.
2. **The web GUI cannot provide operator input**, which a production fixture
   needs (serial per unit, start/stop, prompt responses). A native console
   solves that *and* presents all fixtures in one window.

Choose **Option A** only if you decide the stations can be **monitor-only** with
serials supplied by a scanner/console — then it's far less code.

## 5. Suggested PyQt architecture (sketch, not a commitment)

- **PyQt main process** owns the window and spawns **one OpenHTF worker
  subprocess per fixture**. Each worker runs the existing `build_test()` loop.
- **Operator input flows down; state/records flow up.** IPC options, simplest →
  richest:
  1. `multiprocessing.Queue` between main and each worker (simplest; pass
     serial/commands down, push status/records up).
  2. Each worker writes JSON lines to stdout; the GUI reads/parses them.
  3. Each worker runs its own `StationServer` and the GUI subscribes to its
     SockJS feed (reuses OpenHTF's existing serialization; heaviest).
- **Records & analysis stay separate** (as already prototyped): workers emit the
  JSON records via output callbacks; analysis consumes them from the central
  store. The GUI is for *running*, not analytics.
- Keep workers as real subprocesses (not threads) to honor the one-test-per-process
  constraint and get fault isolation.

---

### Reference files (installed `openhtf` 1.6.1)

- `output/servers/pub_sub.py` — SockJS pub/sub base
- `output/servers/station_server.py` — `StationWatcher` state push; no prompt endpoint
- `output/servers/dashboard_server.py` — multicast multi-station discovery
- `core/test_descriptor.py` — `Test.execute()` one-test-per-process guard

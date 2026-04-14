# Copilot Review Instructions

This repository is a **Home Assistant custom integration** for [Ecocito](https://www.ecocito.com).
The following guidelines should inform every code review.

---

## Target environment

- **Python 3.12** — PEP 695 generic syntax (`class Foo[T]`, `type Alias = ...`) is intentional
  and valid; do not flag it as unsupported.
- **Home Assistant 2024.6+** — follow HA integration architecture and naming conventions.
- Code must pass `ruff check` and `ruff format` (config in `.ruff.toml`).

---

## Architecture patterns (intentional — do not flag)

### `config_entry` on coordinators
`EcocitoDataUpdateCoordinator` does not explicitly receive or store `config_entry` in its
constructor. `DataUpdateCoordinator.__init__` automatically sets `self.config_entry =
config_entries.current_entry.get()` when no `config_entry` argument is passed. Since all
coordinators are created and refreshed inside `async_setup_entry`, `current_entry` is
always set by the HA framework at that point. Accessing `coordinator.config_entry` in
entity setup is safe and correct — do not flag this as a potential `AttributeError`.

### Generic type parameters on coordinator / entity description
`EcocitoDataUpdateCoordinator[T]` and `EcocitoSensorEntityDescription[T]` use PEP 695
generic syntax. This is intentional and fully supported by Python 3.12.

### `FrozenOrThawed` parent class
`SensorEntityDescription` uses HA's `FrozenOrThawed` metaclass, not a standard
`@dataclass(frozen=True)`. Subclassing it with `@dataclasses.dataclass(frozen=True, kw_only=True)`
is the recommended HA pattern (see `homeassistant/components/pvoutput/sensor.py`).

### Single `WasteDepotVisitsDataUpdateCoordinator` per year
Waste-depot visits are account-wide (not per address). A single coordinator instance is
created per year offset and shared across all address devices. Sensor deduplication is
handled in `sensor.py::async_setup_entry` via `registered_waste_depot`.

### Address discovery at setup time
`get_addresses()` is called once in `async_setup_entry`. Adding or removing addresses
on the Ecocito account requires reloading the integration. This is a documented
limitation, not a bug.

### `verify_cleanup` fixture override
`tests/conftest.py` overrides the upstream `verify_cleanup` fixture from
`pytest-homeassistant-custom-component` to add `_run_safe_shutdown_loop` to the
thread allowlist (a daemon thread created by Python 3.12 + aiohttp internals).
The override **replicates all upstream task/timer leak checks** — it does not disable them.

### `aioresponses` with `re.compile` patterns
`aioresponses` 0.7.x does not match base URLs against requests with query params.
All collection/depot URLs are matched with `re.compile(re.escape(base_url))`.

---

## HA integration conventions to enforce

- **`native_unit_of_measurement`** (not `unit_of_measurement`) on `SensorEntityDescription`.
- **`StateType`** (`homeassistant.helpers.typing`) as return type for `native_value`
  and value functions.
- **`SensorStateClass.TOTAL`** for monotonically-increasing cumulative values (total
  collections, total weight). **`SensorStateClass.MEASUREMENT`** for point-in-time or
  non-monotonic values (latest collection weight).
- **`@dataclasses.dataclass(frozen=True, kw_only=True)`** for `SensorEntityDescription`
  subclasses with typed fields — no custom `__init__`.
- **`unique_id`** must include the integration `DOMAIN` as a prefix to avoid collisions
  with other integrations.
- **`ConfigEntryAuthFailed`** raised (not `UpdateFailed`) when credentials expire, so HA
  can prompt the user to re-authenticate.
- **`NumberSelector`** (not raw `vol.Coerce(int)`) for numeric options flow fields so the
  HA UI renders an appropriate input widget.
- Exception handling in HTTP calls: separate `aiohttp.ClientResponseError` (4xx/5xx →
  `InvalidAuthenticationError` for 401/403, `EcocitoError` otherwise) from
  `aiohttp.ClientError` (network → `CannotConnectError`). This applies to **all** methods
  that use `raise_for_status=True`: `authenticate()`, `get_collection_events()`, and
  `get_waste_depot_visits()`. `ClientResponseError` is a subclass of `ClientError` and
  must be caught first.

---

## Out of scope for this integration

- **Periodic address re-discovery**: not implemented; reload is the intended mechanism.
- **`async_migrate_entry`**: the config entry data/options schema is backward-compatible;
  no migration is needed (existing keys use `.get()` with defaults).
- **Multiple config entries**: `single_config_entry: true` in `manifest.json` prevents
  duplicate entries; the config flow does not need an explicit `unique_id` check.

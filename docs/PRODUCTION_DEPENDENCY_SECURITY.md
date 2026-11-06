# Production Dependency Security

Updated: 2026-11-06

The production dependency gate is based on the committed npm lockfile plus independent Python runtime and CI audits.

## Audit evidence (2026-11-02)

The recorded audit artifact found two high-severity npm findings and vulnerable Python packages in both the runtime and CI graphs.

| Ecosystem | Locked package | Locked version | Required patched floor |
|---|---|---:|---:|
| npm | `vite` | `6.4.3` | `6.4.5` |
| npm | `re2js` | `2.8.6` | `2.8.7` |
| Python | `Pillow` | `12.3.0` | `13.0.0` |
| Python | `pyasn1` | `0.6.4` | `0.6.5` |
| Python | `filelock` | `4.0.10` | `4.2.1` |
| Python | `certifi` | `2026.7.22` | `2026.10.19` |
| Python | `opentelemetry-api` | `1.45.0` | `1.45.1` |
| Python | `setuptools` | `84.0.0` | `84.1.0` |

The source requirement inputs now declare the Python security floors. The npm lockfile refresh uses `npm audit fix --package-lock-only`. The daily dependency-lock refresh workflow regenerates the hash-locked Python runtime and CI lockfiles, audits the resulting graphs, and opens a reviewed dependency PR.

## Exception policy

No active dependency-audit exceptions are currently approved. Expired Expo build-tooling exceptions were removed after confirming they were not present in the 2026-11-02 high/critical npm audit findings. Do not add an exception merely to make CI green. Any future exception must identify an exact package/advisory, a concrete compensating control, an accountable owner, and a short expiry date.

## Clinical and release boundary

Dependency audit success is engineering evidence only. It is not clinical validation, regulatory clearance, privacy approval, or authorization to use real patient data.

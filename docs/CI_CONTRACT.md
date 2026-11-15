# DermCareAI CI Contract

**Purpose:** Describe the validation commands configured in the repository workflows. This is a source-level workflow inventory, not a statement that any particular branch or PR has passed.

## Pull-request gates

Source: `.github/workflows/pull-request-gates.yml`

| Job | Configured checks |
|---|---|
| `synchronize-lockfiles` | Regenerates Python runtime and CI lockfiles with pinned `uv`; regenerates `webapp/package-lock.json`; fails when committed lockfiles drift |
| `backend-regression` | Installs hash-locked test requirements; runs `compileall`, `pytest -q tests`, and rejects committed `.pth`, `.keras` and `.h5` model files |
| `pwa-capacitor-regression` | Installs locked PWA dependencies; runs TypeScript, lint, tests and production build; generates/synchronizes the Capacitor Android project; checks that active Expo/React Native package references are absent from `webapp/` |
| `capacitor-ios-regression` | Runs the PWA production build and generates/synchronizes the Capacitor iOS project on macOS |
| `web-dashboard` | Runs frontend lint, build and tests in `webapp/` |

The PWA/Capacitor workflow does **not** run Expo web export, Expo Doctor, Expo prebuild or React Native TypeScript checks. Its Expo/React Native text search is a negative guard: it fails if active package references remain in the production PWA source tree. A guard mentioning a retired technology is not a build or deployment dependency on that technology.

## Continuous evaluation

Source: `.github/workflows/continuous-evaluation.yml`

The scheduled/manual and configured push/PR workflow runs backend compile/safety tests and PWA lint/tests/build with Capacitor Android generation/synchronization. It is a separate evaluation workflow; its result must be checked for the exact commit being assessed.

## Data and release validation workflows

| Workflow | Configured purpose |
|---|---|
| `postgres-staging.yml` | Starts PostgreSQL, initializes schemas, runs selected persistence tests and asserts durable stores use PostgreSQL |
| `staging-acceptance.yml` | Starts the staging stack, runs migrations and selected clinical/commerce acceptance tests |
| `production-preflight.yml` | Runs production-preflight and AI production-gate contract tests |
| `firestore-rules.yml` | Validates Firestore Security Rules using the repository's configured rules-test workflow |
| `dependency-audit.yml` | Produces dependency/security audit evidence; interpret findings against the exact commit |
| `codeql.yml` | Runs CodeQL analysis for configured languages |
| `disaster-recovery-drill.yml` | Exercises the configured backup/restore drill; record its own evidence |
| `container-release.yml` | Builds the governed container/release artifacts under its configured trigger and gates |

## Migration acceptance alignment

The canonical PWA is `webapp/`; Capacitor wraps the same web bundle. No Expo/React Native build, export, prebuild or deployment workflow is used for the current PWA/Capacitor release. CI deliberately contains a check that rejects active Expo/React Native package references in `webapp/`.

## Evidence rules

- A workflow definition proves only what is configured, not that the job passed.
- Record the exact source commit, workflow run, job, conclusion and relevant artifact/log when reporting validation.
- A skipped job is not a pass.
- A green subset of jobs is not an overall green CI result.
- Software CI is necessary engineering evidence; it is not clinical validation, regulatory approval, privacy approval or production authorization.
- Workflow inventory should be reviewed when workflow YAML changes. Do not keep historical commands in this contract after they are removed from the active workflow implementation.

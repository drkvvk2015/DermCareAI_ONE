# DermCareAI v4 Platform Architecture

## Product direction

DermCareAI v4 is structured as a **clinical operating system with AI decision support**, rather than a collection of unrelated clinic features.

The architecture prioritizes:

- clinician-controlled workflows
- explicit AI abstention and provenance
- secure identity and role enforcement
- request correlation and privacy-safe observability
- versioned platform contracts
- domain isolation so billing, pharmacy, notifications and AI can evolve independently
- production deployment boundaries that can be strengthened without changing clinical behaviour

## Runtime layers

```text
+--------------------------------------------------------------+
|                 Clinician Experience                         |
|  Dashboard / Command Center / Patient / Encounter / AI      |
+-------------------------------+------------------------------+
                                |
                                | Firebase identity + API contracts
                                v
+--------------------------------------------------------------+
|                 DermCareAI Platform API v1                   |
|                                                              |
|  Clinical   AI Governance   Billing   Pharmacy   Messaging  |
|     |            |             |        |          |        |
|     +------------+-------------+--------+----------+        |
|                         Audit / Policy                       |
+-------------------------------+------------------------------+
                                |
                                v
+--------------------------------------------------------------+
|                Reliability + Safety Plane                    |
|  Request IDs | Readiness | Model Registry | Metrics         |
+-------------------------------+------------------------------+
                                |
                                v
+--------------------------------------------------------------+
|        Controlled Infrastructure / Data / Model Storage      |
+--------------------------------------------------------------+
```

## v4 platform contracts

The new /api/v1 platform contract exposes:

- /api/v1/platform
- /api/v1/health/live
- /api/v1/health/ready
- /api/v1/ai/policy
- /api/v1/observability/metrics

These endpoints separate application functionality from infrastructure state and establish a stable integration boundary for the mobile application, monitoring, deployment systems and future web clients.

## AI governance contract

Every screening response now carries:

- request correlation ID
- model identity
- model provenance
- confidence threshold
- image-quality safety gate outcome
- abstention state
- explicit non-diagnostic classification
- mandatory human-review requirement
- limitations and safety controls

The application intentionally does **not** equate confidence with diagnostic certainty.

## Reliability

HTTP requests receive a bounded `X-Request-ID` correlation identifier and response timing metadata.

Observability stores aggregate counters only. It does not persist:

- patient names
- patient identifiers
- lesion images
- free-text clinical notes
- access tokens
- payment credentials

## Mobile command centre

The clinician dashboard is being evolved into a platform command centre. It surfaces:

- API version and environment
- readiness state
- authentication enforcement state
- AI safety posture

This makes infrastructure and safety state visible without exposing operational secrets.

## Security posture

The v4 direction keeps existing controls:

- Firebase ID-token verification
- RBAC
- payment signature verification
- server-side payment amount calculation
- pharmacy validation before mutation
- allow-listed notification channels
- hash-chained audit events
- CodeQL
- full regression testing

## Next architecture increments

The next major increments should be implemented as isolated domains:

### 1. Patient 360 / longitudinal record

Create an explicit clinical timeline joining:

- encounters
- appointments
- prescriptions
- images
- AI screening events
- clinician observations
- follow-up plans

### 2. Offline-first sync

Introduce a durable mobile mutation queue with:

- idempotency keys
- optimistic UI
- retry policy
- conflict detection
- sync telemetry

### 3. Multi-clinic tenancy

Move from implicit single-clinic operation to explicit:

```text
Organization
  -> Clinic
      -> Staff / Roles
      -> Patients
      -> Encounters
      -> Inventory
      -> Billing
```

### 4. Event-driven workflows

Convert critical operations into domain events:

```text
PatientCreated
AppointmentScheduled
EncounterRecorded
ScreeningCompleted
InvoiceIssued
PaymentCaptured
MedicineDispensed
NotificationSent
```

Events can then drive analytics, notifications and external integrations without coupling the core clinical transaction to provider APIs.

### 5. AI model registry v2

Track:

- model version
- dataset provenance
- checksum
- intended use
- validation status
- calibration information
- subgroup evaluation
- deployment status
- rollback target

No automatic model promotion from live traffic.

## Production boundary

v4 remains an assistive healthcare software platform. Clinical validation, cybersecurity assessment, data-protection controls, regulatory classification, and deployment-specific operational controls must be completed before using AI output for clinical decision making at scale.

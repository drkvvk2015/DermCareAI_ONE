# DermCareAI Wave 4 — Clinical Product Excellence

## Encounter-centered clinical workflow

Patient 360 now launches a tenant-scoped clinical encounter workspace.

Clinical workflow:

Patient 360
→ Start encounter
→ History
→ Structured dermatology examination
→ Longitudinal lesion capture
→ Assessment and differential
→ Management plan
→ Optional AI decision-support review
→ Follow-up plan
→ Clinician sign-off

## Structured dermatology examination

The mobile workspace records a normalized dermatology section containing:

- onset/duration;
- progression;
- pruritus and pain;
- distribution;
- primary morphology;
- surface/secondary change;
- color;
- border;
- size;
- dermoscopy findings;
- systemic symptoms/red flags.

The backend continues to store this as versioned encounter data, preserving optimistic concurrency.

## Longitudinal lesions

A stable lesion code is scoped to clinic and patient. The encounter can save:

- body site;
- laterality;
- morphology;
- size;
- duration;
- evolution;
- symptoms;
- clinical impression;
- differential.

This supports repeated capture of the same lesion across visits.

## AI review boundary

AI output can be attached to an encounter with:

- request ID;
- model name;
- model provenance;
- predicted label;
- confidence;
- acceptance state.

The clinician can subsequently mark the assessment accepted, rejected, or overridden with an explicit override label.

AI output is decision-support only. The application does not convert a model prediction into a diagnosis automatically.

## Follow-up

Follow-up records are linked to both encounter and patient and contain:

- due date/time;
- instructions;
- planned/completed state;
- creating clinician.

## Sign-off

A signed encounter records:

- signing clinician;
- signing timestamp;
- attestation;
- immutable signed state at the application layer.

Once signed, the current mobile workspace disables editing. Any future amendment should be implemented as a new version/addendum flow rather than silently rewriting the signed record.

## Clinical safety boundary

This workflow improves documentation and traceability but does not by itself establish clinical validity, regulatory authorization, or medical-device classification. AI use must remain within the clinic's approved governance and validation process.

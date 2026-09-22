# DermCareAI v5.1 Swarm Execution Contract

## Objective

Complete the dermatology platform before expanding into other specialties, while keeping `main` stable and enforcing clean-code standards.

## Branch model

- `main`: stable production baseline.
- `develop`: integration branch.
- `feature/clinical-workflow`
- `feature/derm-ai`
- `feature/body-map`
- `feature/procedures`
- `feature/decision-support`
- `feature/patient-experience`
- `feature/analytics`
- `feature/docs-readme`

## Integration rules

1. Feature branches own isolated domain code and tests.
2. Avoid shared-file edits unless the change is contract-driven.
3. Prefer small, reviewable commits.
4. Every feature PR must pass backend regression, mobile type checks, security checks and relevant integration tests.
5. Merge feature PRs into `develop`; validate the integrated application; promote only validated releases to `main`.

## Current wave

| Workstream | Initial implementation |
|---|---|
| Clinical workflow | Structured dermatology history templates + SOAP validation |
| DermAI | Reusable image-quality safety gate |
| Body map | Longitudinal lesion observation contracts |
| Procedures | Structured procedure records with consent requirement |
| Decision support | Deterministic PASI/VASI/SALT scoring primitives |
| Patient experience | Follow-up state contract |
| Analytics | Deterministic cohort metrics |
| Documentation | This execution contract + release-state correction |

## Clean-code contract

- Domain logic remains independent of FastAPI/React UI.
- Public functions have explicit inputs, outputs and validation.
- Deterministic calculations are unit-tested at boundary conditions.
- No PHI is introduced into logging or analytics helpers.
- Feature branches must remain independently reviewable.

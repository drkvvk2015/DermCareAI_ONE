# DermCareAI Final Release Regression Matrix

This matrix is the engineering release gate for the dermatology platform. It separates
automated software evidence from physical-device, clinical-validation, regulatory, and
production-environment evidence.

## Automated critical-path matrix

| Domain | Primary evidence | Gate |
|---|---|---|
| Authentication / RBAC | `backend/tests/test_auth.py` | required |
| Tenant / AI linkage | `backend/tests/test_ai_tenant_linkage.py` | required |
| AI safety | `backend/tests/test_ai_safety.py` | required |
| AI review provenance | `backend/tests/test_ai_review_provenance.py` | required |
| AI production gate | `backend/tests/test_ai_production_gate.py` | required |
| Clinical workflow | `backend/tests/test_clinical_e2e.py` | required |
| Clinical regression | `backend/tests/test_clinical_regression.py` | required |
| Clinical media | `backend/tests/test_clinical_media_contract.py` | required |
| Clinical media + AI provenance | `backend/tests/test_clinical_media_ai_provenance_e2e.py` | required |
| Clinical sign-off | `backend/tests/test_clinical_signoff_documentation.py` | required |
| Body map | `backend/tests/test_body_map.py` | required |
| Billing | `backend/tests/test_billing_math.py` plus billing API contracts | required |
| Audit | `backend/tests/test_audit_contract.py`, `test_audit_store.py` | required |
| Auto-repair safety | `backend/tests/test_auto_repair.py`, `test_auto_repair_ci.py` | required |
| PostgreSQL | staging/migration gate | required |
| Firestore authorization | Firestore Rules workflow | required |
| Security | CodeQL + dependency audit | required |
| Native Android | Expo diagnostics + prebuild + Gradle debug APK | required |

## Prescription -> pharmacy path

The release smoke sequence must cover:

1. Create/select patient.
2. Create dermatology encounter.
3. Create prescription.
4. Confirm prescription is tenant/patient/encounter linked.
5. Submit to pharmacy workflow.
6. Verify duplicate dispense requests are rejected/idempotent.
7. Verify concurrent dispense ownership protection.
8. Verify audit event exists for the dispense operation.
9. Confirm final encounter sign-off remains consistent with prescription state.

## Physical Android smoke

A real-device run must record:

- device model and Android version;
- installed APK version/commit;
- application launch;
- authentication;
- patient search/open;
- encounter create/edit;
- clinical image/media flow;
- AI review and clinician sign-off boundary;
- prescription/pharmacy navigation;
- offline/reconnect behavior;
- crash-free completion of the smoke path.

A successful CI APK build is **not** equivalent to a successful physical-device run.

## Post-merge verification

After PR #174 reaches `main`:

1. Run the complete required CI matrix on the merge commit.
2. Confirm PostgreSQL staging and Firestore rules gates remain green.
3. Confirm CodeQL and dependency audit remain green.
4. Confirm the Android debug APK artifact is produced.
5. Repeat the critical clinical smoke path.
6. Record the merge SHA and workflow run IDs in release evidence.

## Evidence boundaries

The following cannot be marked complete by software CI alone:

- independent clinical validation;
- prospective clinical evaluation;
- AI calibration/subgroup/OOD clinical evidence;
- formal regulatory classification/approval;
- production deployment into a real clinic environment.

Those remain explicit human/accountable evidence gates.

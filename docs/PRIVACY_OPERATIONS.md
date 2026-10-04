# Privacy operations and patient-data requests

This runbook describes the minimum operational handling expected before a clinic uses real patient data. It is not a jurisdiction-specific retention schedule or a substitute for the clinic's approved privacy policy. A named clinic privacy lead must complete the deployment-specific decisions below.

## Handling rule

Never place patient names, IDs, images, clinical details, credentials, or incident evidence in public GitHub issues, pull requests, CI logs/artifacts, or this repository. Use an organization-approved case system and refer to requests here only by an opaque internal case number.

## Required owners before go-live

Record and approve:

- the clinic privacy lead and the technical incident contact;
- the identity-verification method for a patient or authorized representative;
- the applicable retention schedule, legal-hold process, and deletion approval authority;
- approved secure delivery and encryption methods for patient exports;
- the provider contacts and contractual process for PostgreSQL, Firebase/Firestore where used, media storage, messaging, payments, and backups;
- incident severity, escalation contacts, and the jurisdiction-specific notification decision owner.

Do not choose retention periods in code or delete clinical records solely because consent was withdrawn. Those decisions depend on the clinic's approved policy and applicable obligations.

## Consent withdrawal

1. Receive the request through the clinic's approved channel and verify identity outside GitHub.
2. Record the internal case number, consent purpose, document version, request time, and staff actor in the clinic's approved system. Do not copy identifying details into logs.
3. Using an authorized clinic account, call `POST /api/v1/clinical/consents` with the patient identifier, purpose, document version, `status: "withdrawn"`, and a timezone-qualified `withdrawn_at` timestamp.
4. Confirm the response records the withdrawal and that `GET /api/v1/clinical/consents/{patient_id}/active?purpose={purpose}` returns `active: false`.
5. Confirm new signed upload authorization and clinical-media metadata creation for that purpose are denied. Preserve existing records and media pending the retention/legal-hold decision.
6. Route any request to erase already stored data through the data-access/deletion procedure below. The current application does not automatically remove existing media or other clinical records after withdrawal.

The consent endpoint withdraws prior granted consent records for the same clinic, patient, and purpose, writes a withdrawal record, and emits an audit event. Consent withdrawal blocks later consent-gated media operations; it is not itself a deletion operation.

## Access, export, correction, and deletion requests

1. Verify the requester and authority using the clinic's approved method. Do not put identity documents or the request itself in GitHub.
2. Assign an internal case number and have the privacy lead determine scope, deadlines, applicable exceptions, and any legal hold.
3. Inventory all systems in the clinic's approved data map. Current API coverage includes tenant-scoped clinical summaries and media metadata; this is not a complete patient-data export across all application and provider stores.
4. Have an authorized staff member assemble the response from each in-scope system. A second authorized person reviews identity matching, completeness, third-party information, and access scope.
5. Deliver only through the clinic-approved secure channel. Record the delivery and systems checked under the internal case number, without retaining the export in GitHub or CI.
6. For correction or deletion, obtain the policy owner's decision, check retention obligations and holds, execute the approved provider-specific action, verify it, and retain a minimal non-PHI audit record.

The repository has no complete patient export endpoint and no coordinated deletion workflow spanning clinical and commerce databases, Firebase/Firestore, media storage, vendors, logs, and backups. Do not claim these rights workflows are automated until that coverage is implemented and verified.

## Retention and media lifecycle

Clinical media records can carry `retention_until`, but the application does not currently run a retention scheduler or delete the corresponding external object automatically. Before production use, the deployment owner must define a retention matrix for each data class and provider, include legal holds and backup expiry, and document who verifies deletion. Add automation only after the policy and object-store deletion contract are approved.

## Security or privacy incident

1. Open a restricted internal incident record and assign an incident lead. Keep PHI and secrets out of GitHub.
2. Preserve relevant audit and infrastructure evidence. Do not alter audit records while investigating.
3. Contain the access path: disable or revoke affected accounts/tokens, rotate exposed credentials, isolate affected services, and involve the provider as appropriate.
4. Determine affected systems, data categories, time range, and potential patients using approved access. Keep evidence references in the restricted incident record.
5. The clinic privacy lead and counsel determine notification duties and deadlines for the deployment jurisdiction; the technical team supplies verified facts and timestamps.
6. Recover from a known-good state, validate tenant boundaries and audit integrity, document actions, and track corrective work to closure.

## Production readiness checklist

- [ ] Privacy lead, security incident lead, and on-call contacts are named.
- [ ] Data-flow inventory covers databases, Firebase/Firestore where used, media, vendors, logs, and backups.
- [ ] Consent withdrawal has been exercised and its limits are understood.
- [ ] Export, correction, deletion, retention, and legal-hold processes have accountable owners and recorded evidence.
- [ ] Secure response channels and incident escalation have been exercised without using real PHI in GitHub or CI.
- [ ] Automated retention and deletion gaps are accepted with a dated remediation owner, or have been implemented and verified.
- [ ] `PRIVACY_OPERATIONS_APPROVED=true` and `PRIVACY_POLICY_VERSION` identify the approved clinic policy used by this deployment.

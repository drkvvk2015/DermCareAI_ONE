# Dermatology Clinical Flow Completion Checklist

This checklist is the release contract for the clinician-facing dermatology workflow.

- [ ] Patient selected and tenant context established
- [ ] Encounter created and linked to patient
- [ ] Dermatology history/examination documented
- [ ] Lesion registered and longitudinal identity retained
- [ ] Appropriate clinical-media consent recorded
- [ ] Original image stored with provenance metadata
- [ ] AI screening result linked to media and lesion when applicable
- [ ] AI result reviewed/overridden by clinician
- [ ] Required documentation complete
- [ ] Encounter sign-off blocks incomplete documentation or pending AI review
- [ ] Prescription linked to patient and encounter
- [ ] Pharmacy dispensing validates prescription, tenant, and patient
- [ ] FEFO allocation is atomic
- [ ] Billing is deterministic and tenant scoped
- [ ] Follow-up is linked to the encounter/patient
- [ ] Audit events exist for sensitive workflow transitions
- [ ] Cross-tenant access is rejected
- [ ] PostgreSQL staging and production-preflight gates pass
- [ ] Mobile TypeScript/export checks pass
- [ ] Full regression and clinical E2E suites pass

This is an engineering release checklist, not a statement of clinical validation or regulatory approval.

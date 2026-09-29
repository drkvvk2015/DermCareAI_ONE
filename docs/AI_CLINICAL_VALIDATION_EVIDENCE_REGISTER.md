# AI Clinical Validation Evidence Register

Status is intentionally evidence-based. No row may be marked PASS from software CI alone.

| Evidence item | Required artifact | Current status |
|---|---|---|
| Intended use | signed intended-use statement | OUTSTANDING |
| Locked model artifact | immutable model hash + registry record | ENGINEERING CONTROL PRESENT; EXTERNAL VALIDATION OUTSTANDING |
| Locked test set | versioned dataset manifest and provenance | OUTSTANDING |
| Independent/external validation | protocol + blinded results + accountable analysis | OUTSTANDING |
| Sensitivity / specificity | prespecified endpoint analysis | OUTSTANDING |
| PPV / NPV | prespecified endpoint analysis | OUTSTANDING |
| ROC-AUC / PR-AUC | prespecified where appropriate | OUTSTANDING |
| Calibration | prespecified calibration analysis | OUTSTANDING |
| Subgroup analysis | predefined clinically relevant subgroups | OUTSTANDING |
| OOD behavior | OOD test set + abstention behavior | OUTSTANDING |
| Abstention performance | threshold rationale + performance | OUTSTANDING |
| Clinician override analysis | agreement/disagreement + safety analysis | OUTSTANDING |
| Prospective evaluation | approved protocol + real-world evidence | OUTSTANDING |
| Human factors | workflow/usability evidence for clinician review | OUTSTANDING |
| Version/change control | model/software version mapping | ENGINEERING CONTROL PRESENT |
| Post-deployment monitoring | drift, incident, rollback thresholds | OUTSTANDING |

## Evidence integrity rules

- Do not fabricate patient counts, performance values, confidence intervals, subgroup results, or approvals.
- Use a frozen model artifact and locked test set for each validation cycle.
- Record dataset provenance and inclusion/exclusion criteria.
- Predefine primary endpoints and analysis methods before unblinding results.
- Keep clinician adjudication and AI outputs separately auditable.
- Record failures, abstentions and overrides rather than suppressing them.
- A software test passing means the software control worked; it does not establish clinical effectiveness or safety.

## Release decision boundary

The clinical AI gate remains closed until accountable clinical reviewers have reviewed the intended use,
validation protocol, results, subgroup/OOD evidence, safety analysis, and any required independent validation.

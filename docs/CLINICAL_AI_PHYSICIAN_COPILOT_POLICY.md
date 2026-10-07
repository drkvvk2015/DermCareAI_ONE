# DermCareAI — Physician Clinical AI Copilot Policy

## Clinical objective

DermCareAI Clinical AI is a **physician decision-support copilot**. The physician is always the final decision-maker and remains accountable for the diagnosis, investigations, treatment, prescription, referral, and signed clinical record.

The system may suggest:

- differential diagnoses and supporting/contradicting clinical features;
- recommended history and examination elements that may reduce diagnostic uncertainty;
- appropriate investigations and rationale;
- treatment options, contraindications, interactions, precautions, monitoring and follow-up;
- referral/escalation considerations and red-flag warnings;
- patient counselling and safety-netting points;
- guideline-based pathways relevant to the documented diagnosis and patient context.

AI suggestions must never be represented as guaranteed, definitive, or 100% accurate medical decisions. The product target is **comprehensive, evidence-grounded decision support**, not an accuracy guarantee.

## Evidence-grounded clinical reasoning

For each clinically material recommendation, the copilot should prefer authoritative, current sources in this order where applicable:

1. national regulatory/public-health guidance and the applicable hospital policy;
2. current specialty-society clinical practice guidelines;
3. high-quality systematic reviews and consensus statements;
4. authoritative drug/product information and pharmacovigilance sources;
5. high-quality primary studies when higher-level guidance is unavailable or when the question is specifically about new evidence.

Every externally sourced recommendation should retain provenance containing:

- source organization;
- document/guideline title;
- publication or update date;
- version/revision where available;
- stable source URL or document identifier;
- retrieval timestamp;
- relevant recommendation/section identifier where available.

The copilot must not silently present stale evidence as current evidence.

## Freshness policy

Clinical guidance is time-sensitive. The evidence layer must distinguish:

- current/verified guidance;
- superseded guidance;
- conflicting guidance;
- insufficient evidence;
- evidence that could not be verified.

When current authoritative guidance cannot be verified, the UI must explicitly state that limitation rather than inventing or extrapolating a guideline recommendation.

## Patient-context safety

Treatment suggestions must be conditioned on available patient factors, including when relevant:

- age and pregnancy status;
- allergies;
- renal/hepatic function;
- comorbidities;
- current medicines and interactions;
- previous treatment failures/adverse effects;
- immunosuppression;
- relevant laboratory/imaging findings;
- diagnosis certainty;
- red flags and emergency features.

If a material patient factor is missing, the copilot should identify the missing information before presenting a high-consequence recommendation.

## Human-in-the-loop boundary

The copilot may draft or suggest content but may not autonomously:

- finalize a diagnosis;
- prescribe or transmit a prescription;
- alter a signed clinical record;
- order a high-consequence investigation or treatment;
- suppress a safety alert;
- declare a patient safe for discharge;
- promote a diagnostic model or clinical policy.

The physician must explicitly review and accept/modify the relevant content before it becomes part of the signed clinical record.

## Uncertainty and abstention

The copilot must abstain or escalate when:

- available information is insufficient;
- red flags suggest urgent/emergency assessment;
- the proposed treatment has a high-risk contraindication that cannot be resolved;
- authoritative guidance is conflicting or unavailable;
- the model is outside its validated population/use case;
- the clinical image is inadequate for the requested task;
- the recommendation would require a diagnosis that has not been established sufficiently.

The UI must make uncertainty visible and must not convert a model score into a probability unless that score has been explicitly validated and calibrated for the stated use.

## Clinical AI operating modes

### Assistive mode — production

Allowed for controlled clinical use when the hospital has approved the workflow and governance requirements. The physician remains the final decision-maker.

### Diagnostic model mode — evidence gated

Remains disabled until the exact model artifact, validation package, intended use, approvals, governance assessment, deployment evidence and applicable regulatory requirements are complete.

## Clinical-use acceptance criteria

Before declaring the copilot ready for routine clinical use, the organization should complete:

- clinical governance approval;
- intended-use and exclusion criteria;
- privacy/consent assessment;
- cybersecurity review;
- medication-safety review for treatment suggestions;
- source/evidence provenance verification;
- clinician usability and safety testing;
- incident reporting and escalation workflow;
- audit-log verification;
- rollback/kill-switch testing;
- post-deployment monitoring plan;
- accountable clinical owner.

## Product wording

Preferred UI wording:

> **AI Clinical Copilot — decision support only. Physician verification required.**

Avoid wording such as:

> 100% accurate diagnosis

or

> AI-confirmed diagnosis

because those statements are not scientifically or clinically defensible.

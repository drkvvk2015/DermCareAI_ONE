# Security Policy

DermCareAI handles clinical, identity, billing, pharmacy, and audit data. Security reports are treated as private disclosures and should not be posted publicly before remediation.

## Supported versions

| Version | Security support |
| --- | --- |
| Latest `5.1.x` patch | Supported |
| Earlier `5.1.x` patches | Upgrade to the latest patch |
| `5.0.x`, `4.x`, and older | Unsupported |

Security fixes target the latest patch release in the current `5.1.x` line and the active development branch.

## Reporting a vulnerability

Please report suspected vulnerabilities privately through the repository's GitHub Security Advisories channel:

**GitHub → Security → Advisories → Report a vulnerability**

Repository maintainers must enable private vulnerability reporting in repository settings for this route to be available. If it is unavailable, contact the repository owner privately through the contact method listed on the owner's GitHub profile. Do not use a public issue, discussion, pull request, or commit message.

Do not include real patient data, access tokens, service-account keys, production credentials, or other regulated information in the report. Use synthetic identifiers and sanitized logs.

Include, where available:

- affected component, endpoint, or workflow;
- impact and security boundary involved;
- reproduction steps or a minimal proof of concept;
- affected version/commit;
- logs or screenshots with secrets and patient identifiers removed.

## Response expectations

We aim to acknowledge a report within **3 business days**, provide an initial triage decision within **7 business days**, and provide an update at least every **14 calendar days** while it remains open. We coordinate a remediation and disclosure timeline based on severity and exploitability.

Reports may be declined when they are duplicates, are not security issues, or cannot be reproduced. Valid reports may result in a private fix, regression test, release note, and coordinated advisory.

## Clinical-data handling

Never test a production deployment with real patient information unless the test is explicitly authorized and governed by the clinic's privacy, security, and clinical validation procedures. Security testing should use synthetic data by default.

## Scope

Security boundaries include tenant isolation, authentication and authorization, upload handling, clinical record access, AI inference endpoints, payment/commerce integrations, notifications, audit logging, secrets, CI/CD, and deployment configuration.

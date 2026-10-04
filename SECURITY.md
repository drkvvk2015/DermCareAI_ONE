# Security Policy

DermCareAI handles clinical, identity, billing, pharmacy, and audit data. Security reports are treated as private disclosures and should not be posted publicly before remediation.

## Supported versions

| Version | Security support |
| --- | --- |
| main / current production release | Supported |
| Older releases | Best effort; upgrade to the current supported release |

Security fixes are prioritized for the current production release and the active development branch.

## Reporting a vulnerability

Please report suspected vulnerabilities privately through the repository's GitHub Security Advisories channel:

**GitHub → Security → Advisories → Report a vulnerability**

Do not include real patient data, access tokens, service-account keys, production credentials, or other regulated information in the report. Use synthetic identifiers and sanitized logs.

Include, where available:

- affected component, endpoint, or workflow;
- impact and security boundary involved;
- reproduction steps or a minimal proof of concept;
- affected version/commit;
- logs or screenshots with secrets and patient identifiers removed.

## Response expectations

We aim to acknowledge a report within **3 business days**, provide an initial triage decision within **7 business days**, and coordinate a remediation and disclosure timeline based on severity and exploitability.

Reports may be declined when they are duplicates, are not security issues, or cannot be reproduced. Valid reports may result in a private fix, regression test, release note, and coordinated advisory.

## Clinical-data handling

Never test a production deployment with real patient information unless the test is explicitly authorized and governed by the clinic's privacy, security, and clinical validation procedures. Security testing should use synthetic data by default.

## Scope

Security boundaries include tenant isolation, authentication and authorization, upload handling, clinical record access, AI inference endpoints, payment/commerce integrations, notifications, audit logging, secrets, CI/CD, and deployment configuration.

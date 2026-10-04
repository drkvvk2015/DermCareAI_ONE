# Production Dependency Security

Updated: 2026-10-04

The production dependency gate is based on the committed npm lockfile plus an independent Python audit.

- The mobile application is on Expo SDK 57 / React Native 0.86.3.
- @react-native-community/datetimepicker is pinned to 9.2.1; current package security inventory reports zero direct vulnerabilities for that release.
- Firestore's nested @grpc/grpc-js dependency is overridden to 1.14.5 to escape the vulnerable ~1.9.0 dependency range declared by @firebase/firestore.
- The audit workflow retains the complete npm and pip JSON evidence for every run.
- Remediable npm high/critical findings block the release.
- Two exact upstream-unfixed build-tooling advisories are explicitly tracked: GHSA-86w9-cpqp-85rv (node-forge) and GHSA-vfj7-8cjw-p6xm (braces). Current upstream npm releases do not contain fixes for those advisories.
- Those two advisory IDs are non-blocking only when the audit graph proves that the high/critical findings are caused exclusively by those advisories. Every unrelated high/critical advisory remains a hard failure.
- Both exceptions are build-tooling supply-chain risk acceptances, not claims that the affected libraries are safe. Upgrade immediately when fixed upstream releases become available.

This document records the security remediation boundary; it does not constitute a clinical or regulatory approval.

# Production Dependency Security

Updated: 2026-10-04

The production dependency gate is based on the committed npm lockfile plus an independent Python audit.

- The mobile application is on Expo SDK 57 / React Native 0.86.3.
- @react-native-community/datetimepicker is pinned to 9.2.1.
- Firestore's nested @grpc/grpc-js dependency is overridden to 1.14.5 to escape the vulnerable ~1.9.0 dependency range declared by @firebase/firestore.
- The audit workflow retains the complete npm and pip JSON evidence for every run.
- Remediable npm high/critical findings block the release.
- The September 2026 node-forge RSA verification advisory (GHSA-86w9-cpqp-85rv / CVE-2026-85393) is explicitly tracked as upstream-unfixed. The affected copy is pulled by Expo CLI/code-signing build tooling, and no fixed npm release is available yet.
- That exact upstream-unfixed advisory is non-blocking in CI while every unrelated high/critical advisory remains a hard failure.
- This is a documented supply-chain risk acceptance for build tooling, not a claim that the vulnerable library is safe. Upgrade the upstream dependency as soon as a fixed npm release is published.

This document records the security remediation boundary; it does not constitute a clinical or regulatory approval.

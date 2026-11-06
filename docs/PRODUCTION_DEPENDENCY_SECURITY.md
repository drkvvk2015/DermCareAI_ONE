# Production Dependency Security

Updated: 2026-11-06

The production dependency gate is based on the committed npm lockfile plus an independent Python audit.

- The mobile application is on Expo SDK 57 / React Native 0.86.3.
- @react-native-community/datetimepicker is pinned to 9.2.1; current package security inventory reports zero direct vulnerabilities for that release.
- Firestore's nested @grpc/grpc-js dependency is overridden to 1.14.5 to escape the vulnerable ~1.9.0 dependency range declared by @firebase/firestore.
- The audit workflow retains the complete npm and pip JSON evidence for every run.
- Remediable npm high/critical findings block the release.
- The 2026-11-06 web lock refresh removed the `node-forge` and `braces` packages from the resolved dependency graph; their time-limited exceptions have therefore been retired rather than renewed.
- The refreshed graph still contains `deepmerge@4.3.1` through `@rollup/plugin-node-resolve` / `workbox-build`. GitHub Advisory GHSA-gcqx-w48m-w2h4 currently lists no patched release. This is a low-severity build-tooling dependency (marked dev-only in the committed lockfile), not a production runtime dependency; it remains a tracked supply-chain risk, not an assertion of safety. Recheck before each release and remove the dependency path when upstream ships a fix.
- Remediable npm high/critical findings and all Python advisories remain hard failures. Exceptions are time-limited, exact-package, exact-advisory risk acceptances and must not mask unrelated findings.
- The 2026-11-06 Python lock refresh enforces patched floors for certifi, filelock, opentelemetry-api, Pillow, pyasn1 and setuptools; both runtime and CI hash-locked files are regenerated from their authoritative inputs.

This document records the security remediation boundary; it does not constitute a clinical or regulatory approval.

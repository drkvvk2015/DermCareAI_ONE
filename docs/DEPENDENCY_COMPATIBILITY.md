# Dependabot compatibility gate

The reviewed versions and technical evidence for open PRs #175–#182 are in
[`dependency-compatibility.json`](dependency-compatibility.json). The matrix
records an assessment, not merge approval. It deliberately has no auto-merge
behavior. Recheck PR state and candidate CI before acting; the reported check
results are a snapshot from 2026-09-29.

## Status meanings

- **PASS** — evidence and required candidate checks are green; still requires
  normal human review.
- **NEEDS_REVIEW** — plausible to adopt, but listed compatibility checks or
  review are outstanding.
- **HOLD** — a concrete compatibility/coupling issue must be resolved before
  considering the candidate.

## Gate and merge order

1. Re-run/fix candidate checks first. At assessment, all checks on these PRs
   failed and their logs could not be retrieved, so none is marked PASS.
2. Keep the grouped PR #175 split from the React Navigation major upgrade and
   Cloudinary update; preserve security-relevant transitive updates rather than
   discarding them.
3. Run SQLAlchemy (#177) and psycopg (#180) independently, followed by
   PostgreSQL integration with both resolved versions.
4. Validate date-fns (#176), Redis (#178), and react-native-svg (#181) as
   separate candidates with the matrix's targeted checks.
5. Do not merge expo-file-system #179 into the current SDK 52 app. Consider it
   only with a coordinated Expo SDK upgrade and migration of legacy file APIs.
6. Resolve the duplicate Cloudinary changes in #175 and #182 before merging
   either one. Do not combine these updates automatically.

The backend Redis contract test and mobile date-fns behavior test are run by the
existing backend and mobile PR gates, respectively. A test double verifies the
Redis call contract; it does not replace the Redis-server integration required
for PR #178.

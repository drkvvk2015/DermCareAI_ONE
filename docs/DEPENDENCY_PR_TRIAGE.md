# Dependency PR Triage — 29 September 2026

The stable application baseline is Expo SDK 52 / React Native 0.76.9. Dependency updates are
therefore reviewed for compatibility with that baseline before merge.

| PR | Change | Triage |
|---|---|---|
| #179 | expo-file-system 18.0.12 -> 57.0.7 | **Hold for compatibility validation.** This is a large version jump relative to the current Expo 52 baseline and must not be merged without native prebuild/build/runtime evidence. |
| #176 | date-fns 2.30.0 -> 4.4.0 | **Hold for API compatibility review.** Major-version migration can require source-level changes. Search application usage before merge. |
| #175 | 23 npm/yarn grouped updates | **Hold as a batch.** Broad changes should be decomposed or validated as one matrix; do not use green static checks alone as compatibility evidence. |
| #181 | react-native-svg 15.8.0 -> 15.15.5 | **Targeted mobile validation required.** Run Expo diagnostics, native prebuild and Android debug build before merge. |
| #182 | cloudinary-react-native 1.0.1 -> 1.3.0 | **Targeted media-flow validation required.** Validate signed upload/media metadata paths before merge. |
| #178 | redis >=8.1.0,<9 | **Backend compatibility review required.** Validate rate-limit behavior and async/client compatibility in staging. |
| #177 | SQLAlchemy >=2.0.54,<3 | **Database regression required.** Validate migrations, transaction semantics and PostgreSQL staging. |
| #180 | psycopg[binary] >=3.3.6,<4 | **Database regression required.** Validate PostgreSQL staging and migration/connection behavior. |

## Merge gate

No dependency PR should be merged solely because its individual status check is green.

For application/runtime dependencies, the minimum evidence is:

- targeted unit/integration tests;
- TypeScript/build validation where applicable;
- Expo diagnostics and native prebuild for mobile dependencies;
- Android debug build for native/mobile changes;
- PostgreSQL staging for SQLAlchemy/psycopg/Redis backend changes;
- affected clinical, media, pharmacy and billing smoke paths;
- CodeQL and dependency audit.

## Baseline protection

The dependency queue must not silently upgrade the application from its currently validated
Expo/React Native generation. A deliberate framework migration is a separate project with its
own compatibility and regression plan.

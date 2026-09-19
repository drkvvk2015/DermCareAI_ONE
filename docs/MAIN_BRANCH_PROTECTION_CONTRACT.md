# MAIN branch protection contract

Target: `refs/heads/main`

Keep the production branch protected with:

- pull request required;
- at least 1 approving review;
- stale approvals dismissed on push;
- last-push approval;
- Code Owner review;
- all review conversations resolved;
- force-push/delete blocked;
- linear history;
- signed commits where the organization requires them.

Required status checks:

- `backend-regression`
- `mobile-regression`
- `backend-static-and-safety`
- `mobile-quality`
- `Analyze (actions)`
- `Analyze (javascript-typescript)`
- `Analyze (python)`
- `CodeQL`
- `postgres-integration`
- `firestore-rules`
- `staging-acceptance`

The dependency-audit workflow is intentionally an evidence/reporting workflow until its current vulnerability inventory has been triaged to a release-approved level.

The disaster-recovery drill is scheduled/manual and should be part of the release evidence record rather than a per-PR required check.

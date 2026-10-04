# Dependency security and lock maintenance

## Locked installations

Backend deployment installs use `backend/requirements.lock`, generated from `backend/requirements.txt`. Backend pull-request CI installs the smaller regression set from `backend/requirements-ci.lock`, generated from `backend/requirements-ci.in`. Both locks pin transitive versions and package hashes for Python 3.12 across supported platforms.

Regenerate locks from the repository root with `uv`:

```bash
uv pip compile backend/requirements.txt --python-version 3.12 --universal --generate-hashes --output-file backend/requirements.lock
uv pip compile backend/requirements-ci.in --python-version 3.12 --universal --generate-hashes --output-file backend/requirements-ci.lock
```

Review lock changes as code. Run the relevant CI and staging workflows before merging a dependency update. JavaScript applications continue to install from their checked-in `package-lock.json` files with `npm ci`.

## Audit thresholds

The scheduled and pull-request dependency workflow audits both JavaScript lockfiles and both Python lockfiles. It blocks high or critical npm advisories and any known Python vulnerability. The four machine-readable reports are uploaded even when a finding blocks the job.

Temporary exceptions belong in `security/dependency-audit-exceptions.json`. Each exception must identify one ecosystem, package, advisory, owner, reason, and expiry date. The current Expo build-tooling exceptions for `node-forge` and `braces` are limited to the upstream-unfixed advisories recorded in [Production Dependency Security](PRODUCTION_DEPENDENCY_SECURITY.md), and expire on 4 November 2026 unless renewed in a reviewed change. Exceptions expire automatically in the audit checker; wildcard packages, wildcard advisories, and permanent suppressions are not accepted. Prefer updating a lock to a fixed release over granting an exception.

The audit establishes known advisory status for the locked dependency graph at scan time. It does not establish that application code is secure or that a dependency is clinically appropriate.

# Pending CodeSwarm Learnings — Quarantine

Append-only holding area for candidate learnings that cannot safely be committed to the active memory store.

No pending learning is currently recorded.

Each future entry must use this shape:

~~~yaml
### PENDING-<run-id>

run_id: "<unique run id>"
timestamp_utc: "<UTC timestamp>"
task: "<short task summary>"
reason_quarantined: "<validator state and exact reason>"
evidence:
  - "<specific non-sensitive evidence>"
proposed_learning:
  pattern: "<what happened>"
  root_cause: "<evidence-based cause>"
  corrective_rule: "<specific future behavior>"
affected_area: "<module or engineering area>"
promotion_status: "PENDING_VALIDATION"
~~~

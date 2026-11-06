# CodeSwarm Memory Intelligence 3.0

This directory stores durable engineering learnings and the metadata required to validate them.

## Layout

~~~text
.codeswarm/memory/
├── learnings.md
├── schema-version
├── manifest.json
├── prompt-versions.md
├── quarantine/
│   ├── README.md
│   └── pending-learnings.md
└── snapshots/
    └── README.md
~~~

## Integrity dimensions

Memory validation has two independent dimensions:

- **Structural integrity:** record format, unique IDs, ordering, manifest counts, first/latest IDs, schema agreement, safe file references, and required supporting files.
- **Cryptographic consistency:** SHA-256 comparison between the latest learning record and latest_record_hash.

A structurally valid memory store with no stored hash is UNVERIFIED, not FAILURE. A stored digest mismatch is FAILURE.

The digest is calculated over the latest record block. Line endings are normalized to LF, trailing LF characters are removed, and exactly one LF is appended before UTF-8 SHA-256 hashing. The validator is the source of truth for this canonicalization.

A matching digest detects drift relative to the manifest. It is not a digital signature or proof of historical authorship. Use protected branches, reviewed commits, and signed commits where repository policy requires authenticity.

## Validation

From the repository root:

~~~bash
python -B .codeswarm/tools/validate_memory.py --format json
python -B -m unittest discover -s .codeswarm/tests -p "test_*.py" -v
~~~

The validator is read-only. It never repairs files or changes the manifest.

It also returns a deterministic knowledge-graph projection and engineering-intelligence summary derived from the validated learning records. The graph links learning IDs to exact affected-area, pattern and root-cause text. Repeated-pattern statistics group exact text only; similar wording is not merged. These summaries support navigation and prioritization, not causal claims. Do not use the projection as trusted historical guidance when structural validation fails.

Exit codes:

- 0: structural validation passed; cryptographic state is either VERIFIED or UNVERIFIED.
- 1: structural failure or stored digest mismatch.
- 2: validator invocation or execution error.

## Append-only policy

Existing learning records are immutable historical evidence. Add new records at the end of learnings.md; do not rewrite or delete old records.

The current legacy Markdown record format remains supported. New records must use the required fields documented in learnings.md.

## Quarantine policy

When the active memory store fails structural validation or has a digest mismatch:

1. Do not apply the untrusted historical learnings.
2. Do not append to or rewrite the active learning store.
3. Preserve the proposed learning in quarantine/pending-learnings.md.
4. Record the validator diagnostics and the affected manifest fields.
5. Repair the active store only through the Evolver's controlled recovery procedure.
6. Never promote quarantined entries until the active store validates.

A METADATA_ONLY_SAFE repair is limited to rebuilding manifest counts and first/latest IDs from well-formed, unique, ordered learning records. It must not change learning text, schema version, or an existing mismatched cryptographic digest. All other failures require manual review.

## Snapshots

Before a schema migration or prompt evolution, preserve the relevant prior memory files under snapshots/ using a unique run ID and UTC timestamp. Snapshots are immutable and must not contain patient-identifiable information, credentials, tokens, or secrets.

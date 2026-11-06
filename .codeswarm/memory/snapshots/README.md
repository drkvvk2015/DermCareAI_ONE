# CodeSwarm Memory Snapshots

Store immutable pre-migration and pre-prompt-evolution snapshots here.

Use a unique run ID and UTC timestamp in each snapshot directory. Include only the relevant prior versions of:

- learnings.md
- schema-version
- manifest.json
- prompt-versions.md

Do not overwrite or delete an existing snapshot. Never include PHI, credentials, access tokens, secrets, or unnecessary raw logs.

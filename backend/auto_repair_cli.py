"""CLI adapter for producing a conservative CI repair proposal."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

from auto_repair import RepairOrchestrator, RepairPolicy, cluster_failures, propose_repair

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--log', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--allow-path', action='append', default=[])
    parser.add_argument('--deny-path', action='append', default=[])
    parser.add_argument('--attempt', type=int, default=1)
    parser.add_argument('--max-attempts', type=int, default=2)
    parser.add_argument('--idempotency-key')
    args = parser.parse_args()
    log_text = Path(args.log).read_text(encoding='utf-8', errors='replace')
    proposal = propose_repair(log_text)
    key = args.idempotency_key or hashlib.sha256(log_text.encode('utf-8')).hexdigest()
    orchestrator = RepairOrchestrator(
        policy=RepairPolicy(allow_paths=tuple(args.allow_path), deny_paths=tuple(args.deny_path)),
        max_attempts=args.max_attempts,
    )
    report = orchestrator.run(
        log_text,
        idempotency_key=key,
        attempt=args.attempt,
        dry_run=True,
    )
    payload = report.to_dict()
    payload.update({
        'kind': proposal.kind.value,
        'summary': proposal.summary,
        'commands': list(proposal.commands),
        'safe_to_automate': proposal.safe_to_automate,
        'failure_clusters': [
            {
                'fingerprint': cluster.fingerprint,
                'kind': cluster.kind.value,
                'occurrences': cluster.occurrences,
                'example': cluster.example,
                'root_cause_hypothesis': cluster.root_cause_hypothesis,
            }
            for cluster in cluster_failures([log_text])
        ],
    })
    Path(args.output).write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(payload, indent=2))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
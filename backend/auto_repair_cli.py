"""CLI adapter for producing a conservative CI repair proposal."""
from __future__ import annotations
import argparse, json
from pathlib import Path
from auto_repair import propose_repair

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--log', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    proposal = propose_repair(Path(args.log).read_text(encoding='utf-8', errors='replace'))
    payload = {'kind': proposal.kind.value, 'confidence': proposal.confidence, 'summary': proposal.summary, 'commands': list(proposal.commands), 'safe_to_automate': proposal.safe_to_automate}
    Path(args.output).write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(payload, indent=2))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
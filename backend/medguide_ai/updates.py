"""Detect upstream guideline changes and stage them for clinician review.

Nothing here edits approved guideline entries: a detected change only creates a
pending notice. A clinician must review the source, update the approved entry file
(with approved_by/approved_on), then acknowledge the notice.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator

from medguide_ai.core import GuidelineSource

ALLOWED_HOSTS: dict[str, tuple[str, ...]] = {
    "IADVL": ("iadvl.org",),
    "AAD": ("aad.org",),
    "BAD": ("bad.org.uk",),
    "NICE": ("nice.org.uk",),
}
MAX_BYTES = 5_000_000
TIMEOUT_SECONDS = 20
_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,120}$")
REVIEW_OUTCOMES = ("entry_updated", "no_clinical_change")

Fetcher = Callable[[str], bytes]


class MonitoredDocument(BaseModel):
    source: GuidelineSource
    url: str
    label: str = Field(min_length=1)

    @field_validator("url")
    @classmethod
    def _trusted_https_url(cls, value: str) -> str:
        parsed = urlparse(value)
        if parsed.scheme != "https" or not parsed.hostname:
            raise ValueError("monitored URLs must use https")
        return value

    def model_post_init(self, __context: object) -> None:
        host = (urlparse(self.url).hostname or "").lower()
        if not any(host == d or host.endswith("." + d) for d in ALLOWED_HOSTS[self.source]):
            raise ValueError(f"{host} is not an allowed host for {self.source}")


def _fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "DermCareAI-guideline-monitor"})
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:  # noqa: S310 - https + host allowlist enforced
        data = response.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError("document exceeds size limit")
    return data


def _dirs(directory: Path) -> tuple[Path, Path, Path]:
    base = directory / ".updates"
    return base, base / "pending", base / "reviewed"


def load_monitored(directory: Path) -> list[MonitoredDocument]:
    path = directory / "sources.json"
    if not path.is_file():
        return []
    return [MonitoredDocument.model_validate(entry) for entry in json.loads(path.read_text(encoding="utf-8"))]


def check_for_updates(directory: Path, fetch: Fetcher = _fetch) -> dict[str, list]:
    """Fetch each monitored document; record a baseline first, then a pending notice on change."""
    base, pending, _ = _dirs(directory)
    pending.mkdir(parents=True, exist_ok=True)
    state_path = base / "state.json"
    state: dict[str, str] = json.loads(state_path.read_text(encoding="utf-8")) if state_path.is_file() else {}
    result: dict[str, list] = {"baselined": [], "changed": [], "unchanged": [], "errors": []}
    for doc in load_monitored(directory):
        try:
            digest = hashlib.sha256(fetch(doc.url)).hexdigest()
        except Exception as exc:  # network/size errors must not stop other sources
            result["errors"].append({"url": doc.url, "error": type(exc).__name__})
            continue
        previous = state.get(doc.url)
        if previous is None:
            result["baselined"].append(doc.url)
        elif previous == digest:
            result["unchanged"].append(doc.url)
        else:
            now = datetime.now(timezone.utc)
            notice_id = f"{doc.source}-{now.strftime('%Y%m%dT%H%M%SZ')}-{digest[:8]}"
            notice = {
                "id": notice_id,
                "source": doc.source,
                "label": doc.label,
                "url": doc.url,
                "previous_sha256": previous,
                "current_sha256": digest,
                "detected_at": now.isoformat(),
                "status": "pending_review",
            }
            (pending / f"{notice_id}.json").write_text(json.dumps(notice, indent=2), encoding="utf-8")
            result["changed"].append(notice_id)
        state[doc.url] = digest
    state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
    return result


def list_pending(directory: Path) -> list[dict]:
    _, pending, _ = _dirs(directory)
    if not pending.is_dir():
        return []
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(pending.glob("*.json"))]


def acknowledge(directory: Path, notice_id: str, reviewer: str, outcome: str) -> dict:
    if not _ID_RE.fullmatch(notice_id):
        raise ValueError("invalid notice id")
    if outcome not in REVIEW_OUTCOMES:
        raise ValueError("invalid outcome")

    _, pending, reviewed = _dirs(directory)
    notice_path: Path | None = None
    for candidate in pending.glob("*.json"):
        try:
            payload = json.loads(candidate.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if payload.get("id") == notice_id:
            notice_path = candidate
            notice = payload
            break

    if notice_path is None:
        raise FileNotFoundError(notice_id)

    notice.update(
        status="reviewed",
        outcome=outcome,
        reviewed_by=reviewer,
        reviewed_at=datetime.now(timezone.utc).isoformat(),
    )
    reviewed.mkdir(parents=True, exist_ok=True)
    reviewed_path = reviewed / notice_path.name
    reviewed_path.write_text(json.dumps(notice, indent=2), encoding="utf-8")
    notice_path.unlink()
    return notice


def main(argv: list[str] | None = None) -> int:
    import os

    directory = Path(os.getenv("GUIDELINES_DIR", str(Path(__file__).resolve().parent.parent / "guidelines")))
    result = check_for_updates(directory)
    print(json.dumps({k: len(v) for k, v in result.items()}))
    for notice_id in result["changed"]:
        print(f"PENDING REVIEW: {notice_id}")
    return 1 if result["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())

from __future__ import annotations

from backend.ai_adapters.medgemma import MedGemmaAdapter


def test_medgemma_is_disabled_by_default(monkeypatch):
    monkeypatch.delenv("ENABLE_MEDGEMMA", raising=False)
    adapter = MedGemmaAdapter()
    assert adapter.config.enabled is False
    assert adapter.available is False
    assert adapter.status()["error"] == "disabled_by_configuration"


def test_medgemma_status_exposes_governance_boundary(monkeypatch):
    monkeypatch.setenv("ENABLE_MEDGEMMA", "false")
    adapter = MedGemmaAdapter()
    status = adapter.status()
    assert status["model_id"] == "google/medgemma-1.5-4b-it"
    assert status["loaded"] is False

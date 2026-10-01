import logging
from pathlib import Path

from app import ModelService


def test_missing_local_model_weights_do_not_emit_error_log(caplog, monkeypatch, tmp_path):
    monkeypatch.setattr("app.MODEL_DIR", tmp_path)
    monkeypatch.setattr("app.ENABLE_EMBEDDED_DERM_MODEL", False)

    with caplog.at_level(logging.WARNING):
        service = ModelService()
        result = service.load()

    assert result is False
    assert service.mode == "unavailable"
    assert "Local research model weights are not installed" in service.last_error
    assert not any(record.levelno >= logging.ERROR for record in caplog.records)
    assert any("AI model unavailable" in record.message for record in caplog.records)

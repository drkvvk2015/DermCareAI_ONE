import asyncio
import io
import logging
import pytest
from fastapi import HTTPException, UploadFile
from starlette.requests import Request

from app import ModelService, predict


def test_missing_local_model_weights_do_not_emit_error_log(caplog, monkeypatch, tmp_path):
    monkeypatch.setattr("app.MODEL_DIR", tmp_path)
    monkeypatch.setattr("app.ENABLE_EMBEDDED_DERM_MODEL", False)
    monkeypatch.setattr("app.diagnostic_clinical_activation_allowed", lambda: True)

    with caplog.at_level(logging.WARNING):
        service = ModelService()
        result = service.load()

    assert result is False
    assert service.mode == "unavailable"
    assert "Local research model weights are not installed" in service.last_error
    assert not any(record.levelno >= logging.ERROR for record in caplog.records)
    assert any("AI model unavailable" in record.message for record in caplog.records)


def test_model_service_load_fails_closed_when_diagnostic_policy_disallows_execution(monkeypatch):
    monkeypatch.setattr("app.diagnostic_clinical_activation_allowed", lambda: False)

    service = ModelService()

    assert service.load() is False
    assert service.mode == "unavailable"
    assert service.last_error == "Diagnostic inference is disabled by the physician-final Clinical AI policy"


def test_predict_rejects_when_diagnostic_policy_disallows_execution(monkeypatch):
    monkeypatch.setattr("app.diagnostic_clinical_activation_allowed", lambda: False)
    request = Request({"type": "http", "method": "POST", "path": "/predict", "headers": []})
    upload = UploadFile(filename="synthetic.jpg", file=io.BytesIO(b""))

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(predict(request, upload, {"uid": "doctor-1"}))

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "Diagnostic inference is disabled by the physician-final Clinical AI policy"

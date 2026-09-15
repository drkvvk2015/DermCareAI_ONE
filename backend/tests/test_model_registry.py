import json

import model_registry


def test_repository_backed_models_do_not_require_file(tmp_path, monkeypatch) -> None:
    """Verify repository-backed registry entries do not require local model files."""
    registry_path = tmp_path / "registry.json"
    registry_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "models": {
                    "local": {"file": "local.bin", "validated": False},
                    "remote": {"repository": "example/model", "revision": "main", "validated": False},
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(model_registry, "MODEL_REGISTRY_PATH", registry_path)
    result = model_registry.verify_models(str(tmp_path))
    assert result["local"]["exists"] is False
    assert result["remote"]["source"] == "repository"
    assert result["remote"]["repository"] == "example/model"

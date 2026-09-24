from model_registry import production_artifact_eligible


def test_production_ai_is_not_eligible_without_approved_deployment(tmp_path):
    ok, reason = production_artifact_eligible(model_dir=str(tmp_path), app_env="production")
    assert ok is False
    assert "production AI deployment" in reason or "governance" in reason

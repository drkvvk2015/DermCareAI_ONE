from fastapi import HTTPException

import clinical_ai_assist_api as module


def _user():
    return {
        "uid": "doctor-1",
        "roles": {"doctor"},
        "claims": {"organization_id": "org-1", "clinic_id": "clinic-1"},
    }


def test_differential_assist_is_explicitly_non_diagnostic(monkeypatch):
    monkeypatch.setenv("ENABLE_CLINICAL_ASSIST_AI", "true")
    monkeypatch.setattr(
        module,
        "get_encounter",
        lambda encounter_id, organization_id, clinic_id: {
            "id": encounter_id,
            "patient_id": "patient-1",
        },
    )
    monkeypatch.setattr(module, "record_event", lambda *args, **kwargs: None)

    result = module.differential_assist(
        module.DifferentialAssistRequest(
            encounter_id="enc-1",
            primary_morphology="plaque",
            secondary_changes=["scale"],
            distribution="extensor surfaces",
            pruritus=True,
        ),
        _user(),
    )

    assert result["clinical_use"] == "preliminary_assistive_only"
    assert result["diagnostic_status"] == "not_a_diagnosis"
    assert result["requires_clinician_verification"] is True
    assert result["can_sign_diagnosis"] is False
    assert result["can_prescribe"] is False
    assert result["candidates"]
    assert all(item["support_score_is_probability"] is False for item in result["candidates"])


def test_differential_assist_stays_disabled_when_feature_flag_is_off(monkeypatch):
    monkeypatch.setenv("ENABLE_CLINICAL_ASSIST_AI", "false")
    try:
        module.differential_assist(
            module.DifferentialAssistRequest(
                encounter_id="enc-1",
                primary_morphology="plaque",
            ),
            _user(),
        )
    except HTTPException as exc:
        assert exc.status_code == 409
    else:
        raise AssertionError("Clinical assist must be fail-closed when disabled")


def test_differential_assist_requires_tenant_context(monkeypatch):
    monkeypatch.setenv("ENABLE_CLINICAL_ASSIST_AI", "true")
    with_tenant_missing = dict(_user())
    with_tenant_missing["claims"] = {}
    try:
        module.differential_assist(
            module.DifferentialAssistRequest(
                encounter_id="enc-1",
                primary_morphology="plaque",
            ),
            with_tenant_missing,
        )
    except HTTPException as exc:
        assert exc.status_code == 403
    else:
        raise AssertionError("Clinical assist must require tenant context")

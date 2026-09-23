import clinical


def _user(org="org-1", clinic="clinic-1"):
    return {"uid":"doctor-1","claims":{"organization_id":org,"clinic_id":clinic}}


def test_ai_review_rejects_cross_tenant_media(monkeypatch):
    monkeypatch.setattr(clinical, "get_encounter", lambda encounter_id, clinic_id: {"id":encounter_id,"patient_id":"p1"})
    monkeypatch.setattr(clinical, "get_media", lambda *args, **kwargs: None)
    try:
        clinical.post_ai_review("e1", clinical.AIReviewCreate(media_id="m1", request_id="r1", model_name="m", predicted_label="uncertain", confidence=0.2), _user())
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 404
    else:
        raise AssertionError("cross-tenant media must be rejected")


def test_ai_review_rejects_cross_tenant_lesion(monkeypatch):
    monkeypatch.setattr(clinical, "get_encounter", lambda encounter_id, clinic_id: {"id":encounter_id,"patient_id":"p1"})
    monkeypatch.setattr(clinical, "get_lesion", lambda *args, **kwargs: None)
    try:
        clinical.post_ai_review("e1", clinical.AIReviewCreate(lesion_id="l1", request_id="r1", model_name="m", predicted_label="uncertain", confidence=0.2), _user())
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 409
    else:
        raise AssertionError("cross-tenant lesion must be rejected")

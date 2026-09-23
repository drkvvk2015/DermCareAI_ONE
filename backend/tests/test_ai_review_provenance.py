from clinical import AIReviewCreate


def test_ai_review_accepts_media_and_lesion_provenance() -> None:
    req = AIReviewCreate(
        media_id="IMG-1",
        lesion_id="LES-1",
        request_id="REQ-1",
        model_name="research-model",
        predicted_label="melanocytic nevus",
        confidence=0.82,
    )
    assert req.media_id == "IMG-1"
    assert req.lesion_id == "LES-1"


def test_ai_review_provenance_is_optional_for_legacy_assessments() -> None:
    req = AIReviewCreate(
        request_id="REQ-2",
        model_name="research-model",
        predicted_label="uncertain",
        confidence=0.1,
    )
    assert req.media_id is None
    assert req.lesion_id is None

from clinical import ClinicalMediaCreate, EncounterCreate, LesionUpsert


def test_clinical_models_use_isolated_collection_defaults() -> None:
    first = EncounterCreate(patient_id="P1")
    second = EncounterCreate(patient_id="P2")
    first.complaints["chief_complaint"] = "rash"
    assert second.complaints == {}

    lesion_a = LesionUpsert(patient_id="P1", encounter_id="E1", lesion_code="L1", body_site="arm")
    lesion_b = LesionUpsert(patient_id="P1", encounter_id="E1", lesion_code="L2", body_site="leg")
    lesion_a.differential.append("eczema")
    assert lesion_b.differential == []


def test_media_contract_preserves_longitudinal_links() -> None:
    media = ClinicalMediaCreate(
        patient_id="P1",
        encounter_id="E1",
        lesion_id="LES-1",
        object_url="private://media/IMG-1",
        kind="dermoscopy",
        sha256="a" * 64,
        mime_type="image/jpeg",
        byte_size=1024,
        captured_at="2026-09-23T10:00:00+00:00",
    )
    assert media.encounter_id == "E1"
    assert media.lesion_id == "LES-1"

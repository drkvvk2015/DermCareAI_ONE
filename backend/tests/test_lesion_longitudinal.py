from clinical_store import list_lesion_timeline, upsert_lesion


def test_lesion_timeline_preserves_observations()
    first = upsert_lesion(
        organization_id="org-1", clinic_id="clinic-1", patient_id="p-1",
        encounter_id="enc-1", lesion_code="L1", body_site="left forearm",
        morphology={"shape": "papule"}, size_mm=4, duration_days=30,
        evolution="stable", symptoms={"itch": False}, clinical_impression="benign",
        differential=["nevus"], confirmed_diagnosis=None, observed_by="doctor-1",
    )
    upsert_lesion(
        organization_id="org-1", clinic_id="clinic-1", patient_id="p-1",
        encounter_id="enc-2", lesion_code="L1", body_site="left forearm",
        morphology={"shape": "papule"}, size_mm=5, duration_days=60,
        evolution="enlarging", symptoms={"itch": True}, clinical_impression="review",
        differential=["nevus", "melanoma"], confirmed_diagnosis=None, observed_by="doctor-2",
    )
    timeline = list_lesion_timeline(clinic_id="clinic-1", patient_id="p-1", lesion_code="L1")
    assert len(timeline) == 2
    assert timeline[0]["lesion_id"] == first["id"]
    assert timeline[0]["size_mm"] == 4
    assert timeline[1]["size_mm"] == 5
    assert timeline[1]["observed_by"] == "doctor-2"

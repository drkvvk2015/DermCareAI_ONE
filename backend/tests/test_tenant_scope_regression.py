import clinical_store
from sqlalchemy import create_engine


def test_same_clinic_id_different_organizations_are_isolated(monkeypatch, tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'clinical.db'}", future=True)
    monkeypatch.setattr(clinical_store, "ENGINE", engine)
    clinical_store.init_store()

    first = clinical_store.upsert_lesion(
        organization_id="org-a",
        clinic_id="clinic-1",
        patient_id="patient-1",
        encounter_id="enc-a",
        lesion_code="L1",
        body_site="forearm",
    )
    second = clinical_store.upsert_lesion(
        organization_id="org-b",
        clinic_id="clinic-1",
        patient_id="patient-1",
        encounter_id="enc-b",
        lesion_code="L1",
        body_site="face",
    )

    assert first["organization_id"] == "org-a"
    assert second["organization_id"] == "org-b"
    assert first["body_site"] != second["body_site"]

    assert clinical_store.get_lesion(
        first["id"],
        organization_id="org-b",
        clinic_id="clinic-1",
    ) is None
    assert clinical_store.get_lesion(
        second["id"],
        organization_id="org-a",
        clinic_id="clinic-1",
    ) is None


def test_old_clinic_only_unique_key_is_migrated(monkeypatch, tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'legacy.db'}", future=True)
    monkeypatch.setattr(clinical_store, "ENGINE", engine)
    clinical_store.init_store()

    with engine.begin() as conn:
        conn.exec_driver_sql("DROP TABLE lesions")
        conn.exec_driver_sql("""CREATE TABLE lesions (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            clinic_id TEXT NOT NULL,
            patient_id TEXT NOT NULL,
            encounter_id TEXT NOT NULL,
            lesion_code TEXT NOT NULL,
            body_site TEXT NOT NULL,
            laterality TEXT,
            morphology_json TEXT NOT NULL,
            size_mm REAL,
            duration_days INTEGER,
            evolution TEXT,
            symptoms_json TEXT NOT NULL,
            clinical_impression TEXT,
            differential_json TEXT NOT NULL,
            confirmed_diagnosis TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(clinic_id, patient_id, lesion_code)
        )""")
        conn.exec_driver_sql(
            "DELETE FROM schema_migrations WHERE version = 'tenant-scope-v1'"
        )

    clinical_store.init_store()
    a = clinical_store.upsert_lesion(
        organization_id="org-a",
        clinic_id="clinic-1",
        patient_id="patient-1",
        encounter_id="enc-a",
        lesion_code="L1",
        body_site="arm",
    )
    b = clinical_store.upsert_lesion(
        organization_id="org-b",
        clinic_id="clinic-1",
        patient_id="patient-1",
        encounter_id="enc-b",
        lesion_code="L1",
        body_site="leg",
    )
    assert {a["organization_id"], b["organization_id"]} == {"org-a", "org-b"}

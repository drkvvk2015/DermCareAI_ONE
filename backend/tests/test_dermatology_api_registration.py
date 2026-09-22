from app import app

def test_wave2_dermatology_routes_registered():
    paths = set(app.openapi()["paths"])
    assert "/api/v1/dermatology/procedures" in paths
    assert "/api/v1/dermatology/scoring/pasi-component" in paths
    assert "/api/v1/dermatology/followups/validate-transition" in paths
    assert "/api/v1/dermatology/analytics/cohort-summary" in paths

from dermatology.scoring import pasi_component, salt_component, scorable_percentage, vasi_component

def test_scoring_functions_are_deterministic():
    assert pasi_component(1, 1, 1, 2) == 6
    assert vasi_component(10) == 10
    assert salt_component(20) == 20
    assert scorable_percentage(10, 40) == 25

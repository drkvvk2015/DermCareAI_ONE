import pytest
from dermatology.scoring import pasi_component, salt_component, scorable_percentage, vasi_component

def test_pasi_component():
    assert pasi_component(2,1,1,3) == 12

def test_vasi_and_salt():
    assert vasi_component(25) == 25
    assert salt_component(40) == 40

def test_percentage():
    assert scorable_percentage(25,100) == 25

def test_invalid_range():
    with pytest.raises(ValueError):
        vasi_component(101)

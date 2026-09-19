import asyncio

import pytest
from fastapi import HTTPException

from notifications import RegistrationNotification, registration_notifications


def test_unknown_notification_channel_is_rejected() -> None:
    req = RegistrationNotification(
        patient_name="Test",
        phone="9999999999",
        appointment_text="Appointment confirmed",
        channels=["carrier_pigeon"],
    )
    with pytest.raises(HTTPException) as exc:
        asyncio.run(registration_notifications(req, {"uid": "u1", "roles": {"doctor"}}))
    assert exc.value.status_code == 400

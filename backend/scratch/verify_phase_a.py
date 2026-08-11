"""Manual E2E verification script for Phase A."""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from datetime import date, timedelta
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import SessionLocal
from app.models.user import User, RefreshToken
from app.models.trip import Trip

client = TestClient(app)

def run_verification():
    email = "phase_a_verify@test.com"
    
    # 1. Cleanup
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if user:
            db.query(Trip).filter(Trip.user_id == user.id).delete()
            db.query(RefreshToken).filter(RefreshToken.user_id == user.id).delete()
            db.delete(user)
            db.commit()
    finally:
        db.close()

    # 2. Signup & Login
    signup_resp = client.post(
        "/api/v1/auth/signup",
        json={"name": "PhaseA User", "email": email, "password": "Password123!"},
    )
    assert signup_resp.status_code == 201, signup_resp.json()

    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Password123!"},
    )
    assert login_resp.status_code == 200, login_resp.json()
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 3. Create Trip with planning details
    today = date.today()
    create_resp = client.post(
        "/api/v1/trips",
        json={
            "title": "Kyoto Autumn Retreat",
            "destination": "Kyoto, Japan",
            "start_date": today.isoformat(),
            "end_date": (today + timedelta(days=4)).isoformat(),
            "status": "PLANNED",
            "num_travellers": 3,
            "budget": "₹ 75000",
            "special_requirements": "Looking for scenic autumn foliage and temples",
        },
        headers=headers,
    )
    assert create_resp.status_code == 201, create_resp.json()
    trip_data = create_resp.json()
    trip_id = trip_data["id"]

    # Verify lightweight response does NOT contain itinerary
    assert "itinerary" not in trip_data
    print(f"✅ 1. Trip created successfully with ID: {trip_id}")

    # 4. Verify GET /trips/{id} before itinerary generation (itinerary is None)
    detail_before = client.get(f"/api/v1/trips/{trip_id}", headers=headers).json()
    assert detail_before["itinerary"] is None
    assert detail_before["num_travellers"] == 3
    assert detail_before["budget"] == "₹ 75000"
    print("✅ 2. GET /trips/{id} initially returns itinerary = null (shows 'Generate Itinerary')")

    # 5. Verify GET /trips list remains lightweight
    list_resp = client.get("/api/v1/trips", headers=headers).json()
    assert len(list_resp) == 1
    assert "itinerary" not in list_resp[0]
    print("✅ 3. GET /trips list response remains lightweight")

    # 6. Generate Itinerary (mocks Gemini call or calls service)
    from unittest.mock import patch
    from app.schemas.itinerary import ItinerarySchema, DaySchema, ActivitySchema

    mock_itinerary = ItinerarySchema(
        trip_summary="A tranquil 5-day autumn trip to historic Kyoto.",
        days=[
            DaySchema(
                date=today,
                activities=[
                    ActivitySchema(
                        title="Fushimi Inari Taisha",
                        description="Walk through thousands of vermilion torii gates.",
                        approximate_time="Morning",
                        location="Fushimi Ward, Kyoto",
                    ),
                    ActivitySchema(
                        title="Kiyomizu-dera Temple",
                        description="View autumn foliage from the iconic wooden stage.",
                        approximate_time="Afternoon",
                        location="Higashiyama Ward, Kyoto",
                    ),
                ],
            )
        ],
    )

    with patch("app.api.v1.trips.generate_itinerary", return_value=mock_itinerary):
        gen_resp = client.post(
            f"/api/v1/trips/{trip_id}/generate-itinerary",
            headers=headers,
        )
        assert gen_resp.status_code == 200, gen_resp.json()
        print("✅ 4. Generate itinerary endpoint executed successfully")

    # 7. Simulate refresh / navigate away and return (GET /trips/{id})
    detail_after = client.get(f"/api/v1/trips/{trip_id}", headers=headers).json()
    assert detail_after["itinerary"] is not None
    assert detail_after["itinerary"]["trip_summary"] == "A tranquil 5-day autumn trip to historic Kyoto."
    assert len(detail_after["itinerary"]["days"][0]["activities"]) == 2
    print("✅ 5. Refresh / revisit GET /trips/{id} returns persisted itinerary from database")

    # 8. Cleanup
    client.delete(f"/api/v1/trips/{trip_id}", headers=headers)
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if user:
            db.delete(user)
            db.commit()
    finally:
        db.close()

    print("🎉 ALL PHASE A MANUAL VERIFICATIONS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    run_verification()

"""Manual E2E verification script for Phase D flow."""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from unittest.mock import patch

from app.main import app
from app.core.database import SessionLocal
from app.models.user import User, RefreshToken
from app.models.trip import Trip
from app.models.preference import UserPreference
from app.schemas.itinerary import ItinerarySchema, DaySchema, ActivitySchema
from datetime import date, timedelta

client = TestClient(app)

def run_verification():
    email = "phase_d_verify@test.com"
    
    # 1. Cleanup
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if user:
            db.query(Trip).filter(Trip.user_id == user.id).delete()
            db.query(UserPreference).filter(UserPreference.user_id == user.id).delete()
            db.query(RefreshToken).filter(RefreshToken.user_id == user.id).delete()
            db.delete(user)
            db.commit()
    finally:
        db.close()

    # 2. Signup & Login
    client.post("/api/v1/auth/signup", json={"name": "PhaseD User", "email": email, "password": "Password123!"})
    login_resp = client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 3. Simulate Planner inputs collected:
    destination = "Kashmir, India"
    start_date = (date.today() + timedelta(days=1)).isoformat()
    end_date = (date.today() + timedelta(days=5)).isoformat()
    num_travellers = 3  # Parsed from "me and two friends"
    budget = "around ₹30,000 excluding flights"
    special_requirements = "Vegetarian food and avoid long walks"

    # Step 1: POST /api/v1/trips
    create_resp = client.post(
        "/api/v1/trips",
        json={
            "title": f"{destination} Trip",
            "destination": destination,
            "start_date": start_date,
            "end_date": end_date,
            "status": "PLANNED",
            "num_travellers": num_travellers,
            "budget": budget,
            "special_requirements": special_requirements,
        },
        headers=headers,
    )
    assert create_resp.status_code == 201, create_resp.json()
    trip_id = create_resp.json()["id"]
    print(f"✅ 1. Trip created via planner inputs with ID: {trip_id}")

    # Step 2: POST /api/v1/trips/{trip_id}/generate-itinerary
    mock_itinerary = ItinerarySchema(
        trip_summary="A serene 5-day trip to Kashmir tailored for 3 travellers.",
        days=[
            DaySchema(
                date=date.today() + timedelta(days=1),
                activities=[
                    ActivitySchema(
                        title="Shikara Ride on Dal Lake",
                        description="Tranquil boat ride with scenic valley views.",
                        approximate_time="Morning",
                        location="Srinagar",
                    )
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
        print("✅ 2. Gemini itinerary generated and persisted successfully")

    # Step 3: GET /api/v1/trips/{trip_id} (simulates navigation to /app/trips/{trip_id})
    detail_resp = client.get(f"/api/v1/trips/{trip_id}", headers=headers).json()
    assert detail_resp["num_travellers"] == 3
    assert detail_resp["budget"] == "around ₹30,000 excluding flights"
    assert detail_resp["special_requirements"] == "Vegetarian food and avoid long walks"
    assert detail_resp["itinerary"]["trip_summary"] == "A serene 5-day trip to Kashmir tailored for 3 travellers."
    print("✅ 3. GET /trips/{id} returned full details and persisted itinerary for TripDetailsPage view")

    # Cleanup
    client.delete(f"/api/v1/trips/{trip_id}", headers=headers)
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if user:
            db.delete(user)
            db.commit()
    finally:
        db.close()

    print("🎉 ALL PHASE D E2E FLOW VERIFICATIONS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    run_verification()

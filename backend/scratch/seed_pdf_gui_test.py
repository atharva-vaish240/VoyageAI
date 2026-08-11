import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.models.user import User, RefreshToken
from app.models.trip import Trip

client = TestClient(app)

def seed():
    email = "pdf_tester_gui@test.com"
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.email == email).first()
        if u:
            db.query(Trip).filter(Trip.user_id == u.id).delete()
            db.query(RefreshToken).filter(RefreshToken.user_id == u.id).delete()
            db.delete(u)
            db.commit()
    finally:
        db.close()

    client.post("/api/v1/auth/signup", json={"name": "PDF GUI Tester", "email": email, "password": "Password123!"})
    login_resp = client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Trip 1: With Itinerary
    t1 = client.post(
        "/api/v1/trips",
        json={"title": "Grand Kashmir Expedition", "destination": "Kashmir, India", "start_date": "2026-09-01", "end_date": "2026-09-07", "num_travellers": 3, "budget": "$3,500"},
        headers=headers,
    ).json()

    db = SessionLocal()
    try:
        t = db.query(Trip).filter(Trip.id == t1["id"]).first()
        t.itinerary = {
            "trip_summary": "An unforgettable 7-day tour through the breathtaking valleys, alpine meadows, and pristine lakes of Kashmir.",
            "days": [
                {
                    "date": "2026-09-01",
                    "activities": [
                        {"title": "Arrival in Srinagar & Dal Lake Shikara Ride", "description": "Check into luxury houseboat. Take sunset Shikara ride around Lotus gardens.", "approximate_time": "09:00 AM", "location": "Dal Lake, Srinagar"},
                        {"title": "Mughal Gardens Walk", "description": "Explore Nishat Bagh and Shalimar Bagh.", "approximate_time": "02:00 PM", "location": "Nishat Bagh"}
                    ]
                },
                {
                    "date": "2026-09-02",
                    "activities": [
                        {"title": "Gulmarg Meadow & Cable Car", "description": "Ride Phase 1 & Phase 2 Gondola to Apharwat Peak.", "approximate_time": "08:30 AM", "location": "Gulmarg"}
                    ]
                }
            ]
        }
        db.commit()
    finally:
        db.close()

    # Trip 2: Without Itinerary
    t2 = client.post(
        "/api/v1/trips",
        json={"title": "Unplanned Weekend Trip", "destination": "Goa, India", "start_date": "2026-10-10", "end_date": "2026-10-12"},
        headers=headers,
    ).json()

    print(f"SEED_SUCCESS | Email: {email} | Password: Password123! | TripWithItineraryID: {t1['id']} | TripWithoutItineraryID: {t2['id']}")

if __name__ == "__main__":
    seed()

"""Manual E2E verification script for Phase B (Recommendations)."""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from unittest.mock import patch

from app.main import app
from app.core.database import SessionLocal
from app.models.user import User, RefreshToken
from app.models.preference import UserPreference
from app.schemas.recommendation import RecommendationsResponse, RecommendationItem

client = TestClient(app)

def run_verification():
    email = "phase_b_verify@test.com"
    
    # 1. Cleanup
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if user:
            db.query(UserPreference).filter(UserPreference.user_id == user.id).delete()
            db.query(RefreshToken).filter(RefreshToken.user_id == user.id).delete()
            db.delete(user)
            db.commit()
    finally:
        db.close()

    # 2. Signup & Login
    client.post("/api/v1/auth/signup", json={"name": "PhaseB User", "email": email, "password": "Password123!"})
    login_resp = client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 3. Save User Preferences
    client.put(
        "/api/v1/preferences",
        json={"food_preference": "vegetarian", "travel_style": "relaxation"},
        headers=headers,
    )

    # 4. Mock Gemini recommendations
    mock_resp = RecommendationsResponse(
        seasonal_pick=RecommendationItem(
            category="Seasonal Pick",
            destination="Kashmir, India",
            tagline="Shikara rides & snow-capped peaks",
            reason="Optimal autumn foliage and pleasant mountain weather.",
            highlights=["Dal Lake", "Gulmarg Gondola", "Pahalgam Valley"],
        ),
        hidden_gem=RecommendationItem(
            category="Hidden Gem",
            destination="Tirthan Valley, Himachal Pradesh",
            tagline="Unspoiled river beauty & trout fishing",
            reason="Quiet alpine valley away from commercial crowds.",
            highlights=["Great Himalayan National Park", "Jibhi Waterfalls", "Serolsar Lake"],
        ),
        experience_pick=RecommendationItem(
            category="Experience Pick",
            destination="Rishikesh, Uttarakhand",
            tagline="River rafting & spiritual serenity",
            reason="High-energy adventure coupled with serene Ganges retreats.",
            highlights=["White Water Rafting", "Triveni Ghat Aarti", "Beatles Ashram"],
        ),
    )

    with patch("app.api.v1.recommendations.generate_recommendations", return_value=mock_resp):
        res = client.post("/api/v1/recommendations", headers=headers)
        assert res.status_code == 200, res.json()
        data = res.json()

        assert data["seasonal_pick"]["destination"] == "Kashmir, India"
        assert data["hidden_gem"]["destination"] == "Tirthan Valley, Himachal Pradesh"
        assert data["experience_pick"]["destination"] == "Rishikesh, Uttarakhand"
        print("✅ POST /api/v1/recommendations returned all 3 picks structured correctly!")

    # 5. Cleanup
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if user:
            db.query(UserPreference).filter(UserPreference.user_id == user.id).delete()
            db.query(RefreshToken).filter(RefreshToken.user_id == user.id).delete()
            db.delete(user)
            db.commit()
    finally:
        db.close()

    print("🎉 PHASE B VERIFICATION PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    run_verification()

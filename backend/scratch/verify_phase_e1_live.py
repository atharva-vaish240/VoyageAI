"""Manual verification script for Phase E1 using REAL Gemini and REAL Pexels APIs."""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.models.user import User, RefreshToken
from app.models.preference import UserPreference

client = TestClient(app)

def run_live_verification():
    email = "phase_e1_live@test.com"
    
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
    client.post("/api/v1/auth/signup", json={"name": "Live PhaseE1 User", "email": email, "password": "Password123!"})
    login_resp = client.post("/api/v1/auth/login", json={"email": email, "password": password if 'password' in locals() else "Password123!"})
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    print("🚀 Calling POST /api/v1/recommendations with REAL Gemini + REAL Pexels...")
    resp = client.post("/api/v1/recommendations", headers=headers)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    
    data = resp.json()
    print("\n--- LIVE RECOMMENDATIONS RESPONSE SUMMARY ---")
    for cat_key in ["seasonal_pick", "hidden_gem", "experience_pick"]:
        pick = data[cat_key]
        print(f"\n📌 Category: {pick['category']}")
        print(f"   Destination: {pick['destination']}")
        print(f"   Tagline: {pick['tagline']}")
        print(f"   Image Search Term: {pick.get('image_search_term')}")
        img = pick.get("image")
        if img:
            print(f"   📸 Photo URL: {img['url']}")
            print(f"   👤 Photographer: {img['photographer']} ({img['photographer_url']})")
        else:
            print("   ⚠️ Photo: None (Graceful fallback)")

    # 3. Verify exactly 3 categories returned
    assert "seasonal_pick" in data
    assert "hidden_gem" in data
    assert "experience_pick" in data
    print("\n✅ All 3 recommendation categories present.")

    # 4. Cleanup
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if user:
            db.delete(user)
            db.commit()
    finally:
        db.close()

    print("\n🎉 LIVE E1 VERIFICATION COMPLETED SUCCESSFULLY!")

if __name__ == "__main__":
    run_live_verification()

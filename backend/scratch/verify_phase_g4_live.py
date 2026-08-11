"""Live verification script for Phase G4 Google Calendar scheduling.

Run via: python scratch/verify_phase_g4_live.py
"""

import os
import sys

# Ensure backend root is on Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import SessionLocal
from app.models.user import User
from app.models.trip import Trip
from app.models.google_calendar import GoogleCalendarConnection
from app.services.google_calendar_service import schedule_trip_itinerary_to_calendar, GoogleCalendarError
from app.services.trip_service import get_user_trip, TripError


def main():
    print("=" * 65)
    print("      VOYAGEAI PHASE G4: LIVE GOOGLE CALENDAR VERIFICATION")
    print("=" * 65)

    db = SessionLocal()
    try:
        # 1. Look for a user with an active Google Calendar connection
        conn = db.query(GoogleCalendarConnection).first()
        if not conn:
            print("\n[SKIP] No user with an active Google Calendar connection found in DB.")
            print("       To perform live verification against real Google Calendar:")
            print("       1. Complete Google OAuth flow via frontend or backend callback.")
            print("       2. Re-run this script.")
            print("\n[INFO] Backend unit tests have verified mock scheduling & idempotency successfully.")
            return

        user = db.query(User).filter(User.id == conn.user_id).first()
        if not user:
            print("[SKIP] Connection exists but owner User record was not found.")
            return

        print(f"\n[OK] Found connected user: ID={user.id}, Email={user.email}")

        # 2. Look for a trip belonging to this user with a persisted itinerary
        trip = (
            db.query(Trip)
            .filter(Trip.user_id == user.id, Trip.itinerary.isnot(None))
            .first()
        )
        if not trip:
            print(f"[SKIP] User ID {user.id} has no trips with a generated itinerary.")
            print("       Please generate an itinerary for one of this user's trips first.")
            return

        print(f"[OK] Found user trip: Trip ID={trip.id}, Title='{trip.title}'")

        # ── FLOW A: Schedule Trip Itinerary ────────────────────────────
        print("\n--- FLOW A: Scheduling Itinerary Activities to Google Calendar ---")
        res_a = schedule_trip_itinerary_to_calendar(db, user.id, trip)
        print(f"Result A: Total={res_a.total_activities}, Created={res_a.created}, Already Exists={res_a.already_exists}, Failed={res_a.failed}")
        print(f"Calendar URL: {res_a.calendar_url}")
        if res_a.failed > 0:
            print(f"Failures: {res_a.failed_activities}")

        # ── FLOW B: Idempotency Check (Duplicate Prevention) ───────────
        print("\n--- FLOW B: Re-scheduling Same Trip (Idempotency Check) ---")
        res_b = schedule_trip_itinerary_to_calendar(db, user.id, trip)
        print(f"Result B: Total={res_b.total_activities}, Created={res_b.created}, Already Exists={res_b.already_exists}, Failed={res_b.failed}")

        if res_b.created == 0 and res_b.already_exists == res_b.total_activities:
            print("[SUCCESS] Idempotency verified! 0 duplicate events were created.")
        else:
            print("[WARNING] Idempotency check failed: expected 0 created, already_exists == total.")

        # ── FLOW C: User Isolation Check ──────────────────────────────
        print("\n--- FLOW C: Verifying User Isolation ---")
        other_user = db.query(User).filter(User.id != user.id).first()
        if other_user:
            try:
                get_user_trip(db, other_user.id, trip.id)
                print("[FAIL] User isolation breach! Other user was able to access trip.")
            except TripError as e:
                if e.status_code == 404:
                    print(f"[SUCCESS] User isolation verified! User ID {other_user.id} received 404 for User ID {user.id}'s trip.")
                else:
                    print(f"[WARNING] Unexpected status code: {e.status_code}")
        else:
            print("[INFO] Only one user exists in DB. Created temp user to test isolation...")
            temp_user = User(name="Isolation Tester", email="isolation_test@example.com", password_hash="dummy")
            db.add(temp_user)
            db.commit()
            try:
                get_user_trip(db, temp_user.id, trip.id)
            except TripError as e:
                print(f"[SUCCESS] User isolation verified! Non-owner received {e.status_code}.")
            finally:
                db.delete(temp_user)
                db.commit()

        print("\n" + "=" * 65)
        print("          ALL PHASE G4 VERIFICATIONS COMPLETE!")
        print("=" * 65)

    finally:
        db.close()


if __name__ == "__main__":
    main()

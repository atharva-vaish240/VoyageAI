"""Comprehensive tests for Trip Collaboration / Shared Trips feature."""

from datetime import date, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from app.core.database import SessionLocal
from app.main import app
from app.models.preference import UserPreference
from app.models.trip import Trip, TripStatus
from app.models.trip_member import TripMember, MemberRole
from app.models.user import RefreshToken, User

client = TestClient(app)


def _cleanup_user(email: str):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if user:
            db.query(UserPreference).filter(UserPreference.user_id == user.id).delete()
            db.query(TripMember).filter(TripMember.user_id == user.id).delete()
            db.query(Trip).filter(Trip.user_id == user.id).delete()
            db.query(RefreshToken).filter(RefreshToken.user_id == user.id).delete()
            db.delete(user)
            db.commit()
    finally:
        db.close()


def _signup_and_login(email: str, name: str = "Collab User", password: str = "TestPass123!") -> dict:
    client.post("/api/v1/auth/signup", json={"name": name, "email": email, "password": password})
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.json()
    return resp.json()


def _auth_headers(tokens: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


# ── 1. Database Model & Constraints Tests ───────────────────────────

def test_trip_member_creation_and_cascade():
    """Test TripMember model creation, unique constraints, and cascade delete."""
    user_a_email = "db_collab_a@test.com"
    user_b_email = "db_collab_b@test.com"
    _cleanup_user(user_a_email)
    _cleanup_user(user_b_email)

    try:
        tokens_a = _signup_and_login(user_a_email, name="User A")
        tokens_b = _signup_and_login(user_b_email, name="User B")

        db = SessionLocal()
        try:
            user_a = db.query(User).filter(User.email == user_a_email).first()
            user_b = db.query(User).filter(User.email == user_b_email).first()

            # Create trip
            trip = Trip(
                user_id=user_a.id,
                title="DB Test Trip",
                destination="Tokyo",
                start_date=date.today(),
                end_date=date.today() + timedelta(days=5),
                status=TripStatus.PLANNED,
            )
            db.add(trip)
            db.commit()
            db.refresh(trip)

            # Create TripMember
            member = TripMember(
                trip_id=trip.id,
                user_id=user_b.id,
                role=MemberRole.MEMBER,
            )
            db.add(member)
            db.commit()
            db.refresh(member)

            assert member.id is not None
            assert member.trip_id == trip.id
            assert member.user_id == user_b.id
            assert member.role == MemberRole.MEMBER

            # Test duplicate membership constraint
            dup_member = TripMember(
                trip_id=trip.id,
                user_id=user_b.id,
                role=MemberRole.MEMBER,
            )
            db.add(dup_member)
            with pytest.raises(IntegrityError):
                db.commit()
            db.rollback()

            # Test cascade delete when trip is deleted
            db.delete(trip)
            db.commit()

            deleted_member = db.query(TripMember).filter(TripMember.user_id == user_b.id).first()
            assert deleted_member is None
        finally:
            db.close()
    finally:
        _cleanup_user(user_a_email)
        _cleanup_user(user_b_email)


# ── 2. Member Management API & Authorization Tests ───────────────────

def test_owner_can_add_and_list_and_remove_member():
    """Test full owner workflow: add member by email, list members, remove member."""
    owner_email = "owner_collab_flow@test.com"
    collab_email = "collab_flow@test.com"
    _cleanup_user(owner_email)
    _cleanup_user(collab_email)

    try:
        tokens_owner = _signup_and_login(owner_email, name="Owner User")
        tokens_collab = _signup_and_login(collab_email, name="Collab User")

        # Create trip
        trip_res = client.post(
            "/api/v1/trips",
            json={
                "title": "Kyoto Vacation",
                "destination": "Kyoto",
                "start_date": str(date.today() + timedelta(days=10)),
                "end_date": str(date.today() + timedelta(days=15)),
            },
            headers=_auth_headers(tokens_owner),
        )
        assert trip_res.status_code == 201
        trip_id = trip_res.json()["id"]

        # 1. Add member by email
        add_res = client.post(
            f"/api/v1/trips/{trip_id}/members",
            json={"email": collab_email},
            headers=_auth_headers(tokens_owner),
        )
        assert add_res.status_code == 201
        add_data = add_res.json()
        assert add_data["email"] == collab_email
        assert add_data["name"] == "Collab User"
        assert add_data["role"] == "MEMBER"
        assert add_data["trip_id"] == trip_id
        collab_user_id = add_data["user_id"]

        # 2. List members as owner
        list_res = client.get(
            f"/api/v1/trips/{trip_id}/members",
            headers=_auth_headers(tokens_owner),
        )
        assert list_res.status_code == 200
        members = list_res.json()
        assert len(members) == 2
        assert members[0]["role"] == "OWNER"
        assert members[0]["email"] == owner_email
        assert members[1]["role"] == "MEMBER"
        assert members[1]["email"] == collab_email

        # 3. List members as member
        member_list_res = client.get(
            f"/api/v1/trips/{trip_id}/members",
            headers=_auth_headers(tokens_collab),
        )
        assert member_list_res.status_code == 200
        assert len(member_list_res.json()) == 2

        # 4. Remove member as owner
        del_res = client.delete(
            f"/api/v1/trips/{trip_id}/members/{collab_user_id}",
            headers=_auth_headers(tokens_owner),
        )
        assert del_res.status_code == 204

        # Verify member is removed
        list_after = client.get(
            f"/api/v1/trips/{trip_id}/members",
            headers=_auth_headers(tokens_owner),
        )
        assert len(list_after.json()) == 1
    finally:
        _cleanup_user(owner_email)
        _cleanup_user(collab_email)


def test_member_management_validations_and_security():
    """Test validation edge cases: adding owner, duplicate member, non-existent user, non-owner actions."""
    owner_email = "val_owner@test.com"
    user_b_email = "val_user_b@test.com"
    user_c_email = "val_user_c@test.com"
    _cleanup_user(owner_email)
    _cleanup_user(user_b_email)
    _cleanup_user(user_c_email)

    try:
        tokens_owner = _signup_and_login(owner_email, name="Owner")
        tokens_b = _signup_and_login(user_b_email, name="User B")
        tokens_c = _signup_and_login(user_c_email, name="User C")

        trip_res = client.post(
            "/api/v1/trips",
            json={
                "title": "Osaka Trip",
                "destination": "Osaka",
                "start_date": str(date.today() + timedelta(days=5)),
                "end_date": str(date.today() + timedelta(days=8)),
            },
            headers=_auth_headers(tokens_owner),
        )
        trip_id = trip_res.json()["id"]
        owner_user_id = trip_res.json()["user_id"]

        # Attempt to add non-existent email
        res_not_found = client.post(
            f"/api/v1/trips/{trip_id}/members",
            json={"email": "nobody_nonexistent@example.com"},
            headers=_auth_headers(tokens_owner),
        )
        assert res_not_found.status_code == 404

        # Attempt to add the owner
        res_add_owner = client.post(
            f"/api/v1/trips/{trip_id}/members",
            json={"email": owner_email},
            headers=_auth_headers(tokens_owner),
        )
        assert res_add_owner.status_code == 400
        assert "Cannot add the trip owner" in res_add_owner.json()["detail"]

        # Add user_b successfully
        res_add_b = client.post(
            f"/api/v1/trips/{trip_id}/members",
            json={"email": user_b_email},
            headers=_auth_headers(tokens_owner),
        )
        assert res_add_b.status_code == 201

        # Attempt duplicate addition
        res_dup = client.post(
            f"/api/v1/trips/{trip_id}/members",
            json={"email": user_b_email},
            headers=_auth_headers(tokens_owner),
        )
        assert res_dup.status_code == 400
        assert "already a member" in res_dup.json()["detail"]

        # Member user_b attempts to add user_c (should fail - owner only)
        res_member_add = client.post(
            f"/api/v1/trips/{trip_id}/members",
            json={"email": user_c_email},
            headers=_auth_headers(tokens_b),
        )
        assert res_member_add.status_code == 404

        # Member user_b attempts to remove owner (should fail)
        res_remove_owner = client.delete(
            f"/api/v1/trips/{trip_id}/members/{owner_user_id}",
            headers=_auth_headers(tokens_b),
        )
        assert res_remove_owner.status_code == 404

        # Owner attempts to remove self (should fail)
        res_owner_remove_self = client.delete(
            f"/api/v1/trips/{trip_id}/members/{owner_user_id}",
            headers=_auth_headers(tokens_owner),
        )
        assert res_owner_remove_self.status_code == 400
        assert "Cannot remove the trip owner" in res_owner_remove_self.json()["detail"]

        # Unrelated user_c attempts to list members (should fail)
        res_unrelated_list = client.get(
            f"/api/v1/trips/{trip_id}/members",
            headers=_auth_headers(tokens_c),
        )
        assert res_unrelated_list.status_code == 404
    finally:
        _cleanup_user(owner_email)
        _cleanup_user(user_b_email)
        _cleanup_user(user_c_email)


# ── 3. Trip Listing & Filtering Tests ───────────────────────────────

def test_trip_listing_shows_owned_and_shared_trips_without_duplicates():
    """Test that GET /api/v1/trips returns both owned and shared trips with proper roles."""
    user_main_email = "list_main@test.com"
    user_friend_email = "list_friend@test.com"
    user_stranger_email = "list_stranger@test.com"
    _cleanup_user(user_main_email)
    _cleanup_user(user_friend_email)
    _cleanup_user(user_stranger_email)

    try:
        tokens_main = _signup_and_login(user_main_email, name="Main User")
        tokens_friend = _signup_and_login(user_friend_email, name="Friend User")
        tokens_stranger = _signup_and_login(user_stranger_email, name="Stranger User")

        # Trip 1: Owned by main user
        t1_res = client.post(
            "/api/v1/trips",
            json={
                "title": "My Owned Trip",
                "destination": "Paris",
                "start_date": str(date.today() + timedelta(days=20)),
                "end_date": str(date.today() + timedelta(days=25)),
            },
            headers=_auth_headers(tokens_main),
        )
        assert t1_res.status_code == 201
        t1_id = t1_res.json()["id"]

        # Trip 2: Owned by friend, shared with main user
        t2_res = client.post(
            "/api/v1/trips",
            json={
                "title": "Friend's Shared Trip",
                "destination": "Rome",
                "start_date": str(date.today() + timedelta(days=30)),
                "end_date": str(date.today() + timedelta(days=35)),
            },
            headers=_auth_headers(tokens_friend),
        )
        assert t2_res.status_code == 201
        t2_id = t2_res.json()["id"]

        # Friend adds main user as member
        add_res = client.post(
            f"/api/v1/trips/{t2_id}/members",
            json={"email": user_main_email},
            headers=_auth_headers(tokens_friend),
        )
        assert add_res.status_code == 201

        # Trip 3: Owned by stranger (not shared)
        t3_res = client.post(
            "/api/v1/trips",
            json={
                "title": "Stranger Private Trip",
                "destination": "London",
                "start_date": str(date.today() + timedelta(days=40)),
                "end_date": str(date.today() + timedelta(days=45)),
            },
            headers=_auth_headers(tokens_stranger),
        )
        assert t3_res.status_code == 201
        t3_id = t3_res.json()["id"]

        # main user queries /api/v1/trips
        list_res = client.get("/api/v1/trips", headers=_auth_headers(tokens_main))
        assert list_res.status_code == 200
        trips = list_res.json()
        trip_ids = [t["id"] for t in trips]

        assert t1_id in trip_ids
        assert t2_id in trip_ids
        assert t3_id not in trip_ids
        assert len(set(trip_ids)) == len(trip_ids)  # No duplicates

        # Verify roles
        t1_item = next(t for t in trips if t["id"] == t1_id)
        assert t1_item["role"] == "OWNER"
        assert t1_item["is_owner"] is True

        t2_item = next(t for t in trips if t["id"] == t2_id)
        assert t2_item["role"] == "MEMBER"
        assert t2_item["is_owner"] is False

        # Status filter check
        upcoming_res = client.get("/api/v1/trips?status=upcoming", headers=_auth_headers(tokens_main))
        assert upcoming_res.status_code == 200
        upcoming_ids = [t["id"] for t in upcoming_res.json()]
        assert t1_id in upcoming_ids
        assert t2_id in upcoming_ids

        # Stranger does not see main user's trips
        stranger_list = client.get("/api/v1/trips", headers=_auth_headers(tokens_stranger))
        stranger_ids = [t["id"] for t in stranger_list.json()]
        assert t1_id not in stranger_ids
        assert t2_id not in stranger_ids
    finally:
        _cleanup_user(user_main_email)
        _cleanup_user(user_friend_email)
        _cleanup_user(user_stranger_email)


# ── 4. Shared Itinerary Access & Modification Tests ─────────────────

def test_shared_itinerary_access_and_editing():
    """Test that members can view and edit canonical trip itineraries while strangers are blocked."""
    owner_email = "itin_collab_owner@test.com"
    member_email = "itin_collab_member@test.com"
    unrelated_email = "itin_collab_unrelated@test.com"
    _cleanup_user(owner_email)
    _cleanup_user(member_email)
    _cleanup_user(unrelated_email)

    try:
        tokens_owner = _signup_and_login(owner_email, name="Owner")
        tokens_member = _signup_and_login(member_email, name="Member")
        tokens_unrelated = _signup_and_login(unrelated_email, name="Unrelated")

        # Owner creates trip
        trip_res = client.post(
            "/api/v1/trips",
            json={
                "title": "Collaborative Seoul Trip",
                "destination": "Seoul",
                "start_date": "2026-09-01",
                "end_date": "2026-09-03",
            },
            headers=_auth_headers(tokens_owner),
        )
        trip_id = trip_res.json()["id"]

        # Owner sets initial itinerary
        initial_itinerary = {
            "trip_summary": "Original itinerary created by owner.",
            "days": [
                {
                    "date": "2026-09-01",
                    "activities": [
                        {
                            "approximate_time": "10:00 AM",
                            "title": "Arrive at Incheon",
                            "description": "Airport transfer to Seoul.",
                            "location": "Incheon",
                        }
                    ],
                }
            ],
        }
        put_res = client.put(
            f"/api/v1/trips/{trip_id}/itinerary",
            json=initial_itinerary,
            headers=_auth_headers(tokens_owner),
        )
        assert put_res.status_code == 200

        # Add member to trip
        client.post(
            f"/api/v1/trips/{trip_id}/members",
            json={"email": member_email},
            headers=_auth_headers(tokens_owner),
        )

        # 1. Member can view the itinerary
        member_get = client.get(
            f"/api/v1/trips/{trip_id}/itinerary",
            headers=_auth_headers(tokens_member),
        )
        assert member_get.status_code == 200
        assert member_get.json()["trip_summary"] == "Original itinerary created by owner."

        # 2. Member can edit the itinerary
        updated_itinerary = {
            "trip_summary": "Updated together by member!",
            "days": [
                {
                    "date": "2026-09-01",
                    "activities": [
                        {
                            "approximate_time": "12:00 PM",
                            "title": "Myeongdong Food Tour",
                            "description": "Enjoy spicy rice cakes and dumplings.",
                            "location": "Myeongdong",
                        }
                    ],
                }
            ],
        }
        member_put = client.put(
            f"/api/v1/trips/{trip_id}/itinerary",
            json=updated_itinerary,
            headers=_auth_headers(tokens_member),
        )
        assert member_put.status_code == 200
        assert member_put.json()["trip_summary"] == "Updated together by member!"

        # 3. Owner sees member's saved changes on the canonical record
        owner_get = client.get(
            f"/api/v1/trips/{trip_id}/itinerary",
            headers=_auth_headers(tokens_owner),
        )
        assert owner_get.status_code == 200
        assert owner_get.json()["trip_summary"] == "Updated together by member!"

        # 4. Member CANNOT delete the trip (owner only)
        member_del = client.delete(
            f"/api/v1/trips/{trip_id}",
            headers=_auth_headers(tokens_member),
        )
        assert member_del.status_code == 404

        # 5. Member CANNOT edit trip metadata via PATCH (owner only)
        member_patch = client.patch(
            f"/api/v1/trips/{trip_id}",
            json={"title": "Hacked Title"},
            headers=_auth_headers(tokens_member),
        )
        assert member_patch.status_code == 404

        # 6. Unrelated user CANNOT view or edit the itinerary
        unrelated_get = client.get(
            f"/api/v1/trips/{trip_id}/itinerary",
            headers=_auth_headers(tokens_unrelated),
        )
        assert unrelated_get.status_code == 404

        unrelated_put = client.put(
            f"/api/v1/trips/{trip_id}/itinerary",
            json=updated_itinerary,
            headers=_auth_headers(tokens_unrelated),
        )
        assert unrelated_put.status_code == 404
    finally:
        _cleanup_user(owner_email)
        _cleanup_user(member_email)
        _cleanup_user(unrelated_email)


def test_get_trip_detail_owner_member_and_non_member_access():
    """Regression test for shared trip loading bug:

    - Owner can GET their trip.
    - Member can GET the owner's trip.
    - Non-member cannot GET the owner's trip (404).
    - Member can access the shared itinerary.
    - Non-member cannot access the itinerary (404).
    """
    owner_email = "detail_owner@test.com"
    member_email = "detail_member@test.com"
    stranger_email = "detail_stranger@test.com"
    _cleanup_user(owner_email)
    _cleanup_user(member_email)
    _cleanup_user(stranger_email)

    try:
        tokens_owner = _signup_and_login(owner_email, name="Owner User")
        tokens_member = _signup_and_login(member_email, name="Member Atharva")
        tokens_stranger = _signup_and_login(stranger_email, name="Stranger User")

        # 1. Owner creates trip with planning fields and itinerary
        trip_res = client.post(
            "/api/v1/trips",
            json={
                "title": "Swiss Alps Expedition",
                "destination": "Interlaken, Switzerland",
                "start_date": "2026-10-01",
                "end_date": "2026-10-07",
                "num_travellers": 2,
                "budget": "$4,000",
                "special_requirements": "Vegetarian food and scenic hikes.",
            },
            headers=_auth_headers(tokens_owner),
        )
        assert trip_res.status_code == 201
        trip_id = trip_res.json()["id"]

        # Set an itinerary on the trip
        sample_itinerary = {
            "trip_summary": "Explore Interlaken and Jungfraujoch.",
            "days": [
                {
                    "date": "2026-10-01",
                    "activities": [
                        {
                            "approximate_time": "09:00 AM",
                            "title": "Jungfraujoch Train",
                            "description": "Top of Europe scenic train journey.",
                            "location": "Kleine Scheidegg",
                        }
                    ],
                }
            ],
        }
        itin_put = client.put(
            f"/api/v1/trips/{trip_id}/itinerary",
            json=sample_itinerary,
            headers=_auth_headers(tokens_owner),
        )
        assert itin_put.status_code == 200

        # 2. Owner adds Member
        add_member_res = client.post(
            f"/api/v1/trips/{trip_id}/members",
            json={"email": member_email},
            headers=_auth_headers(tokens_owner),
        )
        assert add_member_res.status_code == 201

        # 3. Owner gets trip detail
        owner_trip_res = client.get(
            f"/api/v1/trips/{trip_id}",
            headers=_auth_headers(tokens_owner),
        )
        assert owner_trip_res.status_code == 200
        owner_data = owner_trip_res.json()
        assert owner_data["id"] == trip_id
        assert owner_data["title"] == "Swiss Alps Expedition"
        assert owner_data["destination"] == "Interlaken, Switzerland"
        assert owner_data["role"] == "OWNER"
        assert owner_data["is_owner"] is True
        assert owner_data["itinerary"] is not None
        assert owner_data["itinerary"]["trip_summary"] == "Explore Interlaken and Jungfraujoch."
        assert len(owner_data["members"]) == 2
        assert owner_data["members"][0]["email"] == owner_email
        assert owner_data["members"][0]["role"] == "OWNER"
        assert owner_data["members"][1]["email"] == member_email
        assert owner_data["members"][1]["role"] == "MEMBER"

        # 4. Member (Atharva) gets trip detail - MUST SUCCEED (fixes the bug)
        member_trip_res = client.get(
            f"/api/v1/trips/{trip_id}",
            headers=_auth_headers(tokens_member),
        )
        assert member_trip_res.status_code == 200
        member_data = member_trip_res.json()
        assert member_data["id"] == trip_id
        assert member_data["title"] == "Swiss Alps Expedition"
        assert member_data["destination"] == "Interlaken, Switzerland"
        assert member_data["role"] == "MEMBER"
        assert member_data["is_owner"] is False
        assert member_data["itinerary"] is not None
        assert member_data["itinerary"]["trip_summary"] == "Explore Interlaken and Jungfraujoch."
        assert len(member_data["members"]) == 2
        assert member_data["members"][0]["email"] == owner_email
        assert owner_data["members"][0]["name"] == "Owner User"
        assert member_data["members"][1]["email"] == member_email
        assert member_data["members"][1]["name"] == "Member Atharva"

        # 5. Non-member (Stranger) cannot GET trip detail (404)
        stranger_trip_res = client.get(
            f"/api/v1/trips/{trip_id}",
            headers=_auth_headers(tokens_stranger),
        )
        assert stranger_trip_res.status_code == 404
        assert stranger_trip_res.json()["detail"] == "Trip not found."

        # 6. Member can access the shared itinerary
        member_itin_res = client.get(
            f"/api/v1/trips/{trip_id}/itinerary",
            headers=_auth_headers(tokens_member),
        )
        assert member_itin_res.status_code == 200
        assert member_itin_res.json()["trip_summary"] == "Explore Interlaken and Jungfraujoch."

        # 7. Non-member cannot access the shared itinerary (404)
        stranger_itin_res = client.get(
            f"/api/v1/trips/{trip_id}/itinerary",
            headers=_auth_headers(tokens_stranger),
        )
        assert stranger_itin_res.status_code == 404
        assert stranger_itin_res.json()["detail"] == "Trip not found."
    finally:
        _cleanup_user(owner_email)
        _cleanup_user(member_email)
        _cleanup_user(stranger_email)


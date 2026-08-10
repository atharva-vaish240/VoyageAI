#!/usr/bin/env python3
"""Create an admin user for development/testing.

Usage:
    python -m scripts.create_admin --email admin@voyageai.com --password AdminPass123 --name "Admin User"

If the email already exists, the user's role is promoted to ADMIN.
"""

import argparse
import sys
import os

# Ensure the project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.user import User, UserRole


def main():
    parser = argparse.ArgumentParser(description="Create an admin user.")
    parser.add_argument("--email", required=True, help="Admin email")
    parser.add_argument("--password", required=True, help="Admin password")
    parser.add_argument("--name", default="Admin", help="Admin display name")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == args.email).first()
        if existing:
            if existing.role == UserRole.ADMIN:
                print(f"User {args.email} is already an ADMIN.")
            else:
                existing.role = UserRole.ADMIN
                db.commit()
                print(f"User {args.email} promoted to ADMIN.")
        else:
            user = User(
                name=args.name,
                email=args.email,
                password_hash=hash_password(args.password),
                role=UserRole.ADMIN,
                auth_provider="local",
            )
            db.add(user)
            db.commit()
            print(f"Admin user created: {args.email}")
    finally:
        db.close()


if __name__ == "__main__":
    main()

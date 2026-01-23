"""
Seed database with initial data for development.

Run with: python -m app.db.seed
"""
from app.db.session import SessionLocal, engine, Base
from app.models.member import BoardMember


def seed_board_members(db):
    """Seed initial board members for testing."""
    members = [
        {"email": "admin@themany.com", "name": "Admin User", "role": "admin"},
        {"email": "chair@themany.com", "name": "Board Chair", "role": "chair"},
        {"email": "member1@themany.com", "name": "Board Member 1", "role": "member"},
        {"email": "member2@themany.com", "name": "Board Member 2", "role": "member"},
        {"email": "member3@themany.com", "name": "Board Member 3", "role": "member"},
        # Add your real email for testing
        {"email": "test@example.com", "name": "Test User", "role": "member"},
    ]

    for member_data in members:
        existing = db.query(BoardMember).filter(BoardMember.email == member_data["email"]).first()
        if not existing:
            member = BoardMember(**member_data)
            db.add(member)
            print(f"  Added: {member_data['email']} ({member_data['role']})")
        else:
            print(f"  Exists: {member_data['email']}")

    db.commit()


def seed_all():
    """Run all seed functions."""
    # Create tables
    Base.metadata.create_all(bind=engine)
    print("Tables created.")

    db = SessionLocal()
    try:
        print("\nSeeding board members...")
        seed_board_members(db)
        print("\nSeeding complete!")
    finally:
        db.close()


if __name__ == "__main__":
    seed_all()

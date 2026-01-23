"""
Seed database with initial data for development.

Run with: python -m app.db.seed
"""
from datetime import datetime, timedelta
from app.db.session import SessionLocal, engine, Base
from app.models.member import BoardMember
from app.models.document import Document
from app.models.meeting import Meeting, AgendaItem
from app.models.decision import Decision, Vote
from app.models.idea import Idea, Comment


def seed_board_members(db):
    """Seed initial board members for testing."""
    members = [
        {"email": "admin@themany.com", "name": "Admin User", "role": "admin"},
        {"email": "chair@themany.com", "name": "Board Chair", "role": "chair"},
        {"email": "member1@themany.com", "name": "Board Member 1", "role": "member"},
        {"email": "member2@themany.com", "name": "Board Member 2", "role": "member"},
        {"email": "member3@themany.com", "name": "Board Member 3", "role": "member"},
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


def seed_documents(db):
    """Seed sample documents."""
    admin = db.query(BoardMember).filter(BoardMember.email == "admin@themany.com").first()
    chair = db.query(BoardMember).filter(BoardMember.email == "chair@themany.com").first()

    if db.query(Document).count() > 0:
        print("  Documents already seeded")
        return

    documents = [
        {
            "title": "Q4 2025 Financial Report",
            "type": "financial",
            "description": "Quarterly financial statements and analysis",
            "file_path": "/documents/q4-2025-financial.pdf",
            "uploaded_by_id": admin.id,
            "signing_status": "completed",
            "docusign_envelope_id": "env-12345",
        },
        {
            "title": "Board Resolution - New Partnership",
            "type": "resolution",
            "description": "Resolution to approve strategic partnership with TechCorp",
            "file_path": "/documents/resolution-partnership.pdf",
            "uploaded_by_id": chair.id,
            "signing_status": "pending",
            "docusign_envelope_id": "env-67890",
        },
        {
            "title": "2026 Strategic Plan",
            "type": "strategy",
            "description": "Annual strategic planning document",
            "file_path": "/documents/2026-strategy.pdf",
            "uploaded_by_id": chair.id,
            "signing_status": None,
        },
        {
            "title": "Board Meeting Minutes - January 2026",
            "type": "minutes",
            "description": "Minutes from the January board meeting",
            "file_path": "/documents/minutes-jan-2026.pdf",
            "uploaded_by_id": admin.id,
            "signing_status": "sent",
            "docusign_envelope_id": "env-11111",
        },
        {
            "title": "Compliance Audit Report",
            "type": "audit",
            "description": "Annual compliance audit findings",
            "file_path": "/documents/compliance-audit-2025.pdf",
            "uploaded_by_id": admin.id,
            "signing_status": "completed",
        },
    ]

    for doc_data in documents:
        doc = Document(**doc_data)
        db.add(doc)
        print(f"  Added document: {doc_data['title']}")

    db.commit()


def seed_meetings(db):
    """Seed sample meetings with agendas."""
    chair = db.query(BoardMember).filter(BoardMember.email == "chair@themany.com").first()
    member1 = db.query(BoardMember).filter(BoardMember.email == "member1@themany.com").first()

    if db.query(Meeting).count() > 0:
        print("  Meetings already seeded")
        return

    now = datetime.utcnow()

    # Upcoming meeting
    meeting1 = Meeting(
        title="Q1 2026 Board Meeting",
        description="Regular quarterly board meeting to review Q1 progress",
        scheduled_date=now + timedelta(days=14),
        location="Conference Room A",
        meeting_link="https://zoom.us/j/123456789",
        status="scheduled",
        created_by_id=chair.id,
    )
    db.add(meeting1)
    db.flush()

    # Add agenda items for upcoming meeting
    agenda1 = [
        {"title": "Call to Order", "duration_minutes": 5, "order_index": 1},
        {"title": "Review of Q4 Financials", "duration_minutes": 30, "order_index": 2, "presenter_id": member1.id},
        {"title": "Strategic Partnership Vote", "duration_minutes": 20, "order_index": 3},
        {"title": "New Business", "duration_minutes": 15, "order_index": 4},
        {"title": "Adjournment", "duration_minutes": 5, "order_index": 5},
    ]
    for item in agenda1:
        db.add(AgendaItem(meeting_id=meeting1.id, **item))

    print(f"  Added meeting: {meeting1.title} (upcoming)")

    # Past meeting 1
    meeting2 = Meeting(
        title="January 2026 Board Meeting",
        description="Regular monthly board meeting",
        scheduled_date=now - timedelta(days=7),
        location="Conference Room A",
        meeting_link="https://zoom.us/j/987654321",
        status="completed",
        created_by_id=chair.id,
    )
    db.add(meeting2)
    db.flush()

    agenda2 = [
        {"title": "Call to Order", "duration_minutes": 5, "order_index": 1},
        {"title": "Approval of December Minutes", "duration_minutes": 10, "order_index": 2},
        {"title": "CEO Report", "duration_minutes": 25, "order_index": 3},
        {"title": "Budget Review", "duration_minutes": 30, "order_index": 4},
        {"title": "Adjournment", "duration_minutes": 5, "order_index": 5},
    ]
    for item in agenda2:
        db.add(AgendaItem(meeting_id=meeting2.id, **item))

    print(f"  Added meeting: {meeting2.title} (completed)")

    # Past meeting 2
    meeting3 = Meeting(
        title="Emergency Board Session",
        description="Emergency session to discuss acquisition offer",
        scheduled_date=now - timedelta(days=21),
        location="Virtual",
        meeting_link="https://zoom.us/j/555555555",
        status="completed",
        created_by_id=chair.id,
    )
    db.add(meeting3)
    db.flush()

    agenda3 = [
        {"title": "Acquisition Offer Review", "duration_minutes": 45, "order_index": 1},
        {"title": "Legal Considerations", "duration_minutes": 30, "order_index": 2},
        {"title": "Vote on Response", "duration_minutes": 15, "order_index": 3},
    ]
    for item in agenda3:
        db.add(AgendaItem(meeting_id=meeting3.id, **item))

    print(f"  Added meeting: {meeting3.title} (completed)")

    db.commit()


def seed_decisions(db):
    """Seed sample decisions with votes."""
    chair = db.query(BoardMember).filter(BoardMember.email == "chair@themany.com").first()
    admin = db.query(BoardMember).filter(BoardMember.email == "admin@themany.com").first()
    member1 = db.query(BoardMember).filter(BoardMember.email == "member1@themany.com").first()
    member2 = db.query(BoardMember).filter(BoardMember.email == "member2@themany.com").first()
    member3 = db.query(BoardMember).filter(BoardMember.email == "member3@themany.com").first()

    if db.query(Decision).count() > 0:
        print("  Decisions already seeded")
        return

    now = datetime.utcnow()

    # Open vote 1
    decision1 = Decision(
        title="Approve TechCorp Partnership",
        description="Vote to approve strategic partnership agreement with TechCorp Inc.",
        type="resolution",
        status="open",
        deadline=now + timedelta(days=7),
        created_by_id=chair.id,
    )
    db.add(decision1)
    db.flush()

    # Add some votes
    db.add(Vote(decision_id=decision1.id, member_id=chair.id, vote="yes"))
    db.add(Vote(decision_id=decision1.id, member_id=member1.id, vote="yes"))
    print(f"  Added decision: {decision1.title} (open, 2 votes)")

    # Open vote 2
    decision2 = Decision(
        title="Q1 Budget Allocation",
        description="Approve proposed budget allocation for Q1 2026",
        type="budget",
        status="open",
        deadline=now + timedelta(days=3),
        created_by_id=admin.id,
    )
    db.add(decision2)
    db.flush()

    db.add(Vote(decision_id=decision2.id, member_id=admin.id, vote="yes"))
    print(f"  Added decision: {decision2.title} (open, 1 vote)")

    # Closed decision
    decision3 = Decision(
        title="Reject Acquisition Offer",
        description="Board resolution to reject unsolicited acquisition offer",
        type="resolution",
        status="closed",
        resolution_number="RES-2026-001",
        deadline=now - timedelta(days=14),
        closed_at=now - timedelta(days=14),
        created_by_id=chair.id,
    )
    db.add(decision3)
    db.flush()

    # All members voted
    db.add(Vote(decision_id=decision3.id, member_id=chair.id, vote="yes"))
    db.add(Vote(decision_id=decision3.id, member_id=admin.id, vote="yes"))
    db.add(Vote(decision_id=decision3.id, member_id=member1.id, vote="yes"))
    db.add(Vote(decision_id=decision3.id, member_id=member2.id, vote="no"))
    db.add(Vote(decision_id=decision3.id, member_id=member3.id, vote="abstain"))
    print(f"  Added decision: {decision3.title} (closed, 5 votes)")

    db.commit()


def seed_ideas(db):
    """Seed sample ideas with comments."""
    chair = db.query(BoardMember).filter(BoardMember.email == "chair@themany.com").first()
    admin = db.query(BoardMember).filter(BoardMember.email == "admin@themany.com").first()
    member1 = db.query(BoardMember).filter(BoardMember.email == "member1@themany.com").first()
    member2 = db.query(BoardMember).filter(BoardMember.email == "member2@themany.com").first()

    if db.query(Idea).count() > 0:
        print("  Ideas already seeded")
        return

    # New idea with comments
    idea1 = Idea(
        title="Implement Board Portal Mobile App",
        description="Develop a mobile application for board members to access documents and vote on decisions on the go.",
        status="new",
        submitted_by_id=member1.id,
    )
    db.add(idea1)
    db.flush()

    db.add(Comment(idea_id=idea1.id, author_id=chair.id, content="Great idea! This would improve accessibility significantly."))
    db.add(Comment(idea_id=idea1.id, author_id=member2.id, content="We should ensure it meets security requirements for sensitive documents."))
    db.add(Comment(idea_id=idea1.id, author_id=admin.id, content="I can get quotes from our development partners."))
    print(f"  Added idea: {idea1.title} (new, 3 comments)")

    # Under review
    idea2 = Idea(
        title="Quarterly Town Halls with Employees",
        description="Host quarterly virtual town halls where board members can address employee questions directly.",
        status="under_review",
        submitted_by_id=member2.id,
    )
    db.add(idea2)
    db.flush()

    db.add(Comment(idea_id=idea2.id, author_id=chair.id, content="I support this initiative. Transparency is important."))
    print(f"  Added idea: {idea2.title} (under_review, 1 comment)")

    # Approved
    idea3 = Idea(
        title="ESG Reporting Framework",
        description="Adopt a formal ESG reporting framework to track and communicate our environmental and social impact.",
        status="approved",
        submitted_by_id=admin.id,
    )
    db.add(idea3)
    db.flush()
    print(f"  Added idea: {idea3.title} (approved)")

    # Rejected
    idea4 = Idea(
        title="Reduce Board Size",
        description="Proposal to reduce board size from 6 to 4 members for efficiency.",
        status="rejected",
        submitted_by_id=member1.id,
    )
    db.add(idea4)
    db.flush()

    db.add(Comment(idea_id=idea4.id, author_id=chair.id, content="After discussion, the board feels diversity of perspectives outweighs efficiency gains."))
    print(f"  Added idea: {idea4.title} (rejected, 1 comment)")

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

        print("\nSeeding documents...")
        seed_documents(db)

        print("\nSeeding meetings...")
        seed_meetings(db)

        print("\nSeeding decisions...")
        seed_decisions(db)

        print("\nSeeding ideas...")
        seed_ideas(db)

        print("\nSeeding complete!")
    finally:
        db.close()


if __name__ == "__main__":
    seed_all()

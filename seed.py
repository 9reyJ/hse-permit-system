# seed.py
from database import engine
from models import Employee, Permit, PermitAction
from sqlalchemy.orm import Session

with Session(engine) as db_session:
    # grab the employee you already registered
    me = db_session.query(Employee).filter_by(username="aissa").first()

    permit1 = Permit(
        requester_id=me.id,
        type="hot work",
        status="submitted",
        description="Welding near tank 4",
    )
    permit2 = Permit(
        requester_id=me.id,
        type="confined space",
        status="draft",
        description="Inspection of vessel B",
    )

    db_session.add_all([permit1, permit2])
    db_session.commit()

    # need the permit ids, so query them back after commit
    action1 = PermitAction(
        permit_id=permit1.id,
        actor_id=me.id,
        action="submitted",
        comment="Initial submission",
    )
    db_session.add(action1)
    db_session.commit()

print("Seeded.")
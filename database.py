# database.py
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from models import Base

engine = create_engine("sqlite:///permits.db")

@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

SessionLocal = sessionmaker(bind=engine)

def init_db():
    Base.metadata.create_all(engine)
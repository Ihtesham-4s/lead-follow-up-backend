import os
from dotenv import load_dotenv
from pathlib import Path
from fastapi.responses import FileResponse
from datetime import datetime, timezone
from typing import Literal
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import create_engine, select, func, String, Text, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker, Session

load_dotenv()  # reads the .env file
DATABASE_URL = os.getenv("DATABASE_URL")

# The engine is the connection to PostgreSQL.
engine = create_engine(DATABASE_URL)

# A session is one "conversation" with the database (save, read, etc.).
SessionLocal = sessionmaker(bind=engine)


# Base is the parent class for all our database tables.
class Base(DeclarativeBase):
    pass


# This class becomes a table called "leads" in PostgreSQL.
class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(primary_key=True)      # unique number, auto-generated
    name: Mapped[str] = mapped_column(String(100))
    contact: Mapped[str] = mapped_column(String(100))
    message: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="new")  # new, contacted, booked...
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# Create the "leads" table in the database if it doesn't exist yet.
Base.metadata.create_all(engine)

app = FastAPI()


# What a client must SEND to create a lead (same as before).
class LeadCreate(BaseModel):
    name: str
    contact: str
    message: str


# What we SEND BACK: the saved lead, including id, status and time.
class LeadRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)  # lets Pydantic read database objects

    id: int
    name: str
    contact: str
    message: str
    status: str
    created_at: datetime


# Opens a database session for each request, then closes it afterwards.
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/leads", response_model=LeadRead)
def create_lead(lead: LeadCreate, db: Session = Depends(get_db)):
    new_lead = Lead(**lead.model_dump())  # turn the validated data into a database row
    db.add(new_lead)       # stage it
    db.commit()            # actually save it
    db.refresh(new_lead)   # reload it so we get the id and created_at
    return new_lead


@app.get("/leads", response_model=list[LeadRead])
def list_leads(db: Session = Depends(get_db)):
    # Get all leads, newest first.
    return db.scalars(select(Lead).order_by(Lead.id.desc())).all()


# The only statuses allowed. Anything else is rejected automatically.
LeadStatus = Literal["new", "contacted", "booked", "lost"]


# What a client sends to change a lead's status.
class StatusUpdate(BaseModel):
    status: LeadStatus


# PATCH = change part of an existing record. {lead_id} comes from the URL.
@app.patch("/leads/{lead_id}/status", response_model=LeadRead)
def update_lead_status(lead_id: int, update: StatusUpdate, db: Session = Depends(get_db)):
    lead = db.get(Lead, lead_id)  # find the lead by its id
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    lead.status = update.status
    db.commit()
    db.refresh(lead)
    return lead


# A lead plus two extra fields that help decide who to follow up.
class QueueItem(LeadRead):
    minutes_waiting: int
    overdue: bool


# The follow-up queue: leads that are still open, oldest first.
@app.get("/follow-up-queue", response_model=list[QueueItem])
def follow_up_queue(overdue_after_minutes: int = 15, db: Session = Depends(get_db)):
    open_leads = db.scalars(
        select(Lead)
        .where(Lead.status.in_(["new", "contacted"]))  # booked/lost are finished
        .order_by(Lead.created_at)                     # longest waiting first
    ).all()

    now = datetime.now(timezone.utc)
    queue = []
    for lead in open_leads:
        minutes = int((now - lead.created_at).total_seconds() // 60)
        queue.append(
            QueueItem(
                **LeadRead.model_validate(lead).model_dump(),
                minutes_waiting=minutes,
                overdue=(lead.status == "new" and minutes >= overdue_after_minutes),
            )
        )
    return queue

# Serve the dashboard page. Path(__file__).parent = the folder where main.py lives.
@app.get("/dashboard", include_in_schema=False)
def dashboard():
    return FileResponse(Path(__file__).parent / "dashboard.html")
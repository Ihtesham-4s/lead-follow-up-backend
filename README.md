# Lead Follow-Up Backend

Service businesses lose money when customer enquiries get lost or forgotten.
This backend receives enquiries, saves them as structured leads, tracks their
status, and shows a follow-up queue with overdue leads highlighted.

## Features
- `POST /leads`: receive and save a lead
- `GET /leads`: list all leads
- `PATCH /leads/{id}/status`: update a lead (new, contacted, booked, lost)
- `GET /follow-up-queue`: open leads, longest waiting first, with overdue flag
- `/dashboard`: web page to view the queue, add leads, and update statuses

## Tech stack
Python, FastAPI, Pydantic, SQLAlchemy, PostgreSQL, HTML/JavaScript

## Run locally
1. `python -m venv venv`, then activate it
2. `pip install -r requirements.txt`
3. Create a PostgreSQL database named `lead_follow_up`
4. Copy `.env.example` to `.env` and put in your password
5. `fastapi dev main.py`
6. Open http://127.0.0.1:8000/dashboard

## Roadmap
AI lead classification, deployment, WhatsApp/webhook integration
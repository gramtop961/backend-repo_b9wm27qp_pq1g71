import os
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Any, Dict
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr

from schemas import Inquiry
from database import db, create_document, get_documents

app = FastAPI(title="PsychSphere Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "PsychSphere API is running"}


@app.get("/api/hello")
def hello():
    return {"message": "Hello from PsychSphere backend!"}


@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response: Dict[str, Any] = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": [],
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = db.name if hasattr(db, "name") else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:  # pragma: no cover
                response["database"] = f"⚠️  Connected but Error: {str(e)[:80]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:  # pragma: no cover
        response["database"] = f"❌ Error: {str(e)[:80]}"

    return response


# Email sending utilities
SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
TO_EMAIL = os.getenv("TO_EMAIL") or os.getenv("OWNER_EMAIL")
FROM_NAME = os.getenv("FROM_NAME", "PsychSphere Inquiries")
FROM_EMAIL = os.getenv("FROM_EMAIL") or SMTP_USER or "no-reply@psychsphere.local"


def send_inquiry_email(inquiry: Inquiry) -> None:
    """Send an email notification for a new inquiry. Safe no-op if SMTP not configured."""
    if not (SMTP_HOST and TO_EMAIL):
        # SMTP not configured; skip email silently
        return

    subject = f"New PsychSphere Inquiry from {inquiry.name}"

    html_body = f"""
    <h2>New Inquiry</h2>
    <p><strong>Name:</strong> {inquiry.name}</p>
    <p><strong>Email:</strong> {inquiry.email}</p>
    <p><strong>Phone:</strong> {inquiry.phone or '-'} </p>
    <p><strong>Newsletter:</strong> {"Yes" if inquiry.newsletter_opt_in else "No"}</p>
    <p><strong>Source:</strong> {inquiry.source or "website"}</p>
    <hr/>
    <p>{inquiry.message}</p>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = formataddr((FROM_NAME, FROM_EMAIL))
    msg["To"] = TO_EMAIL
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
        try:
            server.starttls()
        except Exception:
            pass
        if SMTP_USER and SMTP_PASS:
            server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(FROM_EMAIL, [TO_EMAIL], msg.as_string())


@app.post("/inquiries")
async def create_inquiry(inquiry: Inquiry, background_tasks: BackgroundTasks):
    """Create a new inquiry, store it in the database, and send an email notification."""
    try:
        inserted_id = create_document("inquiry", inquiry)
        # Fire-and-forget email notify
        background_tasks.add_task(send_inquiry_email, inquiry)
        return {"status": "ok", "id": inserted_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/inquiries")
def list_inquiries(limit: int = 50):
    """List recent inquiries (capped). Useful for basic admin review."""
    try:
        docs = get_documents("inquiry", {}, limit=limit)
        # Convert ObjectId to str if present
        for d in docs:
            if "_id" in d:
                d["_id"] = str(d["_id"])  # type: ignore
        return {"items": docs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

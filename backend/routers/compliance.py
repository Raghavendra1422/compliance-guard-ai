from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional
from services.agent import run_compliance_agent
import sqlite3
import json
import uuid
import os
from datetime import datetime

router = APIRouter(prefix="/api/v1/compliance", tags=["Compliance"])

# ── Database setup ─────────────────────────────────────────────
DB_PATH = "./compliance_checks.db"

def init_db():
    """Create the database table if it doesn't exist."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS compliance_checks (
            id TEXT PRIMARY KEY,
            status TEXT DEFAULT 'pending',
            loan_data TEXT,
            report TEXT,
            created_at TEXT,
            completed_at TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()


# ── Pydantic schemas ───────────────────────────────────────────
class LoanApplication(BaseModel):
    applicant_name: str = Field(..., example="Ravi Kumar")
    loan_type: str = Field(..., example="home_loan")
    loan_amount_inr: float = Field(..., example=4500000)
    property_value_inr: float = Field(..., example=5000000)
    ltv_ratio: float = Field(..., example=90)
    interest_rate_percent: float = Field(..., example=8.5)
    tenure_years: int = Field(..., example=20)
    applicant_income_monthly: float = Field(..., example=75000)
    cibil_score: int = Field(..., example=720)
    existing_loans: int = Field(default=0, example=1)
    applicant_city: Optional[str] = Field(default="Mumbai", example="Mumbai")
    loan_purpose: Optional[str] = Field(default="purchase", example="purchase")


class CheckStatus(BaseModel):
    check_id: str
    status: str
    message: str


# ── Helper functions ───────────────────────────────────────────
def save_check(check_id: str, loan_data: dict):
    """Save a new compliance check to database."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO compliance_checks (id, status, loan_data, created_at) VALUES (?, ?, ?, ?)",
        (check_id, "pending", json.dumps(loan_data), datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


def update_check(check_id: str, report: dict):
    """Update the check with the completed report."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "UPDATE compliance_checks SET status=?, report=?, completed_at=? WHERE id=?",
        ("completed", json.dumps(report), datetime.now().isoformat(), check_id)
    )
    conn.commit()
    conn.close()


def get_check(check_id: str) -> dict:
    """Fetch a check from the database by ID."""
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT id, status, loan_data, report, created_at, completed_at FROM compliance_checks WHERE id=?",
        (check_id,)
    ).fetchone()
    conn.close()

    if not row:
        return None

    return {
        "check_id": row[0],
        "status": row[1],
        "loan_data": json.loads(row[2]) if row[2] else {},
        "report": json.loads(row[3]) if row[3] else None,
        "created_at": row[4],
        "completed_at": row[5]
    }


def run_check_background(check_id: str, loan_data: dict):
    """Run the compliance agent in the background."""
    try:
        report = run_compliance_agent(loan_data)
        update_check(check_id, report)
        print(f"[DB] Check {check_id} completed successfully")
    except Exception as e:
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            "UPDATE compliance_checks SET status=? WHERE id=?",
            (f"error: {str(e)}", check_id)
        )
        conn.commit()
        conn.close()
        print(f"[DB] Check {check_id} failed: {e}")


# ── API Endpoints ──────────────────────────────────────────────
@router.post("/check", response_model=CheckStatus)
async def submit_compliance_check(
    loan: LoanApplication,
    background_tasks: BackgroundTasks
):
    """
    Submit a loan application for RBI compliance checking.
    Returns a check_id immediately. Use GET /check/{id} to poll for results.
    The check runs in the background (takes 30-60 seconds).
    """
    check_id = str(uuid.uuid4())[:8].upper()
    loan_data = loan.model_dump()

    # Save to DB immediately
    save_check(check_id, loan_data)

    # Run agent in background so API responds instantly
    background_tasks.add_task(run_check_background, check_id, loan_data)

    return CheckStatus(
        check_id=check_id,
        status="pending",
        message=f"Compliance check started. Poll GET /api/v1/compliance/check/{check_id} for results."
    )


@router.get("/check/{check_id}")
async def get_compliance_result(check_id: str):
    """
    Get the result of a compliance check by ID.
    Status will be 'pending' while running, 'completed' when done.
    """
    result = get_check(check_id)

    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"Check ID '{check_id}' not found."
        )

    if result["status"] == "pending":
        return {
            "check_id": check_id,
            "status": "pending",
            "message": "Compliance check is still running. Please wait 30-60 seconds and try again."
        }

    return result


@router.get("/history")
async def get_compliance_history(limit: int = 10):
    """Get the last N compliance checks from the database."""
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT id, status, created_at, completed_at FROM compliance_checks ORDER BY created_at DESC LIMIT ?",
        (limit,)
    ).fetchall()
    conn.close()

    return {
        "total": len(rows),
        "checks": [
            {
                "check_id": r[0],
                "status": r[1],
                "created_at": r[2],
                "completed_at": r[3]
            }
            for r in rows
        ]
    }


@router.get("/stats")
async def get_stats():
    """System statistics — total checks, compliance rate, etc."""
    conn = sqlite3.connect(DB_PATH)

    total = conn.execute("SELECT COUNT(*) FROM compliance_checks").fetchone()[0]
    completed = conn.execute(
        "SELECT COUNT(*) FROM compliance_checks WHERE status='completed'"
    ).fetchone()[0]

    # Count compliant vs non-compliant
    rows = conn.execute(
        "SELECT report FROM compliance_checks WHERE status='completed'"
    ).fetchall()
    conn.close()

    compliant_count = 0
    for row in rows:
        if row[0]:
            report = json.loads(row[0])
            if report.get("overall_compliant"):
                compliant_count += 1

    non_compliant = completed - compliant_count

    return {
        "total_checks": total,
        "completed": completed,
        "pending": total - completed,
        "compliant": compliant_count,
        "non_compliant": non_compliant,
        "compliance_rate": f"{round((compliant_count/completed)*100, 1)}%" if completed > 0 else "N/A"
    }
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from domain import TokenEngine, TokenSource, TokenStatus

app = FastAPI(title="OPD Token Allocation Engine", docs_url=None)
engine = TokenEngine()


class CreateDoctorRequest(BaseModel):
    name: str
    slot_labels: List[str]  # e.g. ["09:00-10:00", "10:00-11:00"]
    capacity_per_slot: int = 5


class DoctorSummary(BaseModel):
    id: int
    name: str


class BookTokenRequest(BaseModel):
    doctor_id: int
    slot_index: int
    patient_name: str
    source: TokenSource


class TokenResponse(BaseModel):
    id: int
    patient_name: str
    source: TokenSource
    doctor_id: int
    slot_index: int
    status: TokenStatus


class AllocationResponse(BaseModel):
    token: TokenResponse
    allocated_slot_index: Optional[int]
    bumped_token: Optional[TokenResponse] = None
    waitlisted: bool


class CancelResponse(BaseModel):
    cancelled: TokenResponse
    promoted: Optional[TokenResponse] = None


@app.post("/doctors", response_model=DoctorSummary)
def create_doctor(body: CreateDoctorRequest) -> DoctorSummary:
    doctor = engine.create_doctor(
        name=body.name,
        slot_labels=body.slot_labels,
        capacity_per_slot=body.capacity_per_slot,
    )
    return DoctorSummary(id=doctor.id, name=doctor.name)


@app.get("/doctors", response_model=List[DoctorSummary])
def list_doctors() -> List[DoctorSummary]:
    return [DoctorSummary(id=d.id, name=d.name) for d in engine.list_doctors()]


@app.get("/doctors/{doctor_id}/schedule")
def get_schedule(doctor_id: int):
    try:
        return engine.get_schedule_for_doctor(doctor_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/tokens/book", response_model=AllocationResponse)
def book_token(body: BookTokenRequest) -> AllocationResponse:
    try:
        result = engine.book_token(
            doctor_id=body.doctor_id,
            slot_index=body.slot_index,
            patient_name=body.patient_name,
            source=body.source,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    def to_token_response(t) -> TokenResponse:
        return TokenResponse(
            id=t.id,
            patient_name=t.patient_name,
            source=t.source,
            doctor_id=t.doctor_id,
            slot_index=t.slot_index,
            status=t.status,
        )

    return AllocationResponse(
        token=to_token_response(result.token),
        allocated_slot_index=result.allocated_slot_index,
        bumped_token=to_token_response(result.bumped_token)
        if result.bumped_token
        else None,
        waitlisted=result.waitlisted,
    )


@app.post("/tokens/{token_id}/cancel", response_model=CancelResponse)
def cancel_token(token_id: int) -> CancelResponse:
    try:
        data = engine.cancel_token(token_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    def to_token_response(t) -> TokenResponse:
        return TokenResponse(
            id=t.id,
            patient_name=t.patient_name,
            source=t.source,
            doctor_id=t.doctor_id,
            slot_index=t.slot_index,
            status=t.status,
        )

    cancelled = to_token_response(data["cancelled"])
    promoted = to_token_response(data["promoted"]) if data["promoted"] else None
    return CancelResponse(cancelled=cancelled, promoted=promoted)


@app.post("/admin/reset")
def reset_all() -> dict:
    """Reset in-memory data (useful during development / simulation)."""
    engine.reset()
    return {"detail": "State cleared"}


@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui() -> object:
    """
    Serve Swagger UI with a custom page title that does not include 'Swagger UI'.
    Also hides version/OAS badges.
    """
    resp = get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title="OPD Token Allocation Engine",
    )
    html = resp.body.decode("utf-8")
    css = """
<style>
  .swagger-ui .info .title small { display: none !important; }
  .swagger-ui .info .title .version-stamp { display: none !important; }
</style>
""".strip()
    html = html.replace("</head>", f"{css}</head>", 1)
    headers = dict(resp.headers)
    headers.pop("content-length", None)
    return HTMLResponse(html, status_code=resp.status_code, headers=headers)

    
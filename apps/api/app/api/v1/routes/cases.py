from fastapi import APIRouter, Depends

from app.api.v1.dependencies import get_repository
from app.core.errors import not_found
from app.repositories.mock_repository import MockRepository, new_id
from app.schemas.clinical import ChildCase, ChildCaseCreate, ChildCaseUpdate, ConsentWithdrawalRequest, ConsentWithdrawalResult, TimelineEvent
from app.services.consent_service import withdraw_consent

router = APIRouter(prefix="/cases", tags=["cases"])


@router.get("", response_model=list[ChildCase])
def list_cases(repo: MockRepository = Depends(get_repository)):
    return [repo.clone(item) for item in repo.cases.values()]


@router.post("", response_model=ChildCase)
def create_case(payload: ChildCaseCreate, repo: MockRepository = Depends(get_repository)):
    case = ChildCase(case_id=new_id("case"), **payload.model_dump())
    repo.cases[case.case_id] = case
    repo.add_audit("case.create", case.case_id, "Case created in mock repository.")
    return repo.clone(case)


@router.get("/{case_id}", response_model=ChildCase)
def get_case(case_id: str, repo: MockRepository = Depends(get_repository)):
    if case_id not in repo.cases:
        raise not_found("Case not found.")
    return repo.clone(repo.cases[case_id])


@router.patch("/{case_id}", response_model=ChildCase)
def update_case(case_id: str, payload: ChildCaseUpdate, repo: MockRepository = Depends(get_repository)):
    if case_id not in repo.cases:
        raise not_found("Case not found.")
    case = repo.cases[case_id]
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(case, key, value)
    repo.add_audit("case.patch", case_id, "Case updated.")
    return repo.clone(case)


@router.get("/{case_id}/timeline", response_model=list[TimelineEvent])
def case_timeline(case_id: str, repo: MockRepository = Depends(get_repository)):
    if case_id not in repo.cases:
        raise not_found("Case not found.")
    events = []
    for session in repo.sessions.values():
        if session.case_id == case_id:
            events.append(TimelineEvent(event_id=new_id("evt"), label=f"Session {session.session_date}", status=session.status, occurred_at=session.created_at, target_id=session.session_id))
    return events


@router.post("/{case_id}/withdraw-consent", response_model=ConsentWithdrawalResult)
def withdraw_case_consent(case_id: str, payload: ConsentWithdrawalRequest, repo: MockRepository = Depends(get_repository)):
    if case_id not in repo.cases:
        raise not_found("Case not found.")
    return withdraw_consent(repo, case_id, payload.reason, payload.redact_notes)

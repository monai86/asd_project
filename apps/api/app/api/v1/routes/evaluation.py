from fastapi import APIRouter

from app.core.errors import bad_request
from app.schemas.clinical import (
    AsrDatasetEvaluationRequest,
    AsrDatasetEvaluationResult,
    AsrEvaluationInput,
    AsrEvaluationReport,
    BaselineEvaluationRequest,
    BaselineEvaluationResult,
    DatasetBuildRequest,
    DatasetBuildResult,
    ModelCardResult,
)
from app.services.asr_evaluation_service import evaluate_asr, evaluate_asr_dataset
from app.services.ml_baseline_service import build_dataset, build_model_card, evaluate_baselines

router = APIRouter(prefix="/evaluation", tags=["evaluation"])


@router.post("/asr", response_model=AsrEvaluationReport)
def evaluate(payload: AsrEvaluationInput):
    return evaluate_asr(payload)


@router.post("/asr-dataset", response_model=AsrDatasetEvaluationResult)
def evaluate_dataset(payload: AsrDatasetEvaluationRequest | None = None):
    request = payload or AsrDatasetEvaluationRequest()
    try:
        return evaluate_asr_dataset(
            dataset_dir=request.dataset_dir,
            hypothesis_dir=request.hypothesis_dir,
            output_dir=request.output_dir,
        )
    except ValueError as exc:
        raise bad_request(str(exc)) from exc


@router.post("/model-card", response_model=ModelCardResult)
def model_card(payload: DatasetBuildRequest | None = None):
    request = payload or DatasetBuildRequest()
    return build_model_card(source_dir=request.source_dir)


@router.post("/ml-dataset", response_model=DatasetBuildResult)
def ml_dataset(payload: DatasetBuildRequest | None = None):
    request = payload or DatasetBuildRequest()
    return build_dataset(request.source_dir, include_unlabeled=request.include_unlabeled)


@router.post("/ml-baseline", response_model=BaselineEvaluationResult)
def ml_baseline(payload: BaselineEvaluationRequest | None = None):
    request = payload or BaselineEvaluationRequest()
    return evaluate_baselines(request.source_dir)

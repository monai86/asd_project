import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

def test_run_actual_training(tmp_path):
    from packages.ml.train_model import load_curated_corpus_features, train_reference_cohort_models
    df = load_curated_corpus_features()
    result = train_reference_cohort_models(
        df,
        artifact_dir=tmp_path / "artifacts",
        model_dir=tmp_path / "models",
        report_dir=tmp_path / "reports" / "metrics",
    )
    print("Training finished:", result)
    assert result is not None

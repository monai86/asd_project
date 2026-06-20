from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
API_ROOT = ROOT / "apps" / "api"
sys.path.insert(0, str(API_ROOT))

from app.schemas.clinical import AsrEvaluationInput
from app.services.asr_evaluation_service import evaluate_asr, evaluate_asr_dataset


def test_asr_evaluation_reports_core_metrics():
    report = evaluate_asr(
        AsrEvaluationInput(
            reference_text="*CHI:\tI see car .",
            hypothesis_text="*CHI:\tI see a car .",
            reference_speakers=["CHI"],
            hypothesis_speakers=["CHI"],
            audio_duration_seconds=10,
            transcribed_duration_seconds=8,
        )
    )

    assert report.coverage == 0.8
    assert report.speaker_accuracy == 1.0
    assert "Normalized WER" in report.markdown


def test_asr_dataset_evaluation_writes_json_and_markdown(tmp_path):
    dataset = tmp_path / "evaluation"
    gold = dataset / "gold_transcripts"
    hypotheses = dataset / "hypothesis_transcripts"
    audio = dataset / "audio_samples"
    gold.mkdir(parents=True)
    hypotheses.mkdir()
    audio.mkdir()
    (gold / "sample_001.cha").write_text("*CHI:\tI see car .\n*THER:\ttell me more .\n", encoding="utf-8")
    (hypotheses / "sample_001.cha").write_text("*CHI:\tI see a car .\n*THER:\ttell me more .\n", encoding="utf-8")
    (audio / "sample_001.wav").write_text("placeholder only; no audio bytes in fixtures", encoding="utf-8")

    result = evaluate_asr_dataset(dataset, output_dir=tmp_path / "reports")

    assert result.sample_count == 1
    assert result.samples[0].sample_id == "sample_001"
    assert result.samples[0].audio_present is True
    assert result.aggregate_metrics["speaker_accuracy"] == 1.0
    assert Path(result.report_paths["json"]).exists()
    assert Path(result.report_paths["markdown"]).read_text(encoding="utf-8").startswith("# ASR Dataset Evaluation Report")

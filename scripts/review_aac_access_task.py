"""Review AAC corpus access and task fit before any raw download.

This script records official AAC corpus-page facts needed for the ASD add-on
review gate. It does not log in to TalkBank, download files, or change
Reference Cohort eligibility rules.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
REFERENCE_DIR = PROJECT_ROOT / "data" / "reference"

OUTPUT_PATH = REFERENCE_DIR / "aac_access_task_review.csv"

CORPUS = "AAC"
OFFICIAL_URL = "https://talkbank.org/asd/access/English/AAC.html"
OFFICIAL_PARTICIPANT_COUNT = 18
OFFICIAL_VIDEO_SUBSET_COUNT = 14
ACCESS_REQUIREMENT = "restricted_to_faculty_slps_or_postdocs"
AGE_ELIGIBILITY_RAW = "over_30_months"
COLLECTION_CONTEXT = (
    "remote_caregiver_mediated_aac_intervention_16_weeks_pre_mid_post_5_min_samples"
)
TASK_FIT_FOR_TOYPLAY = "not_direct_match"
RECOMMENDED_TASK_TYPE = "aac_intervention"
MOR_GRA_WARNING = (
    "child_vocal_emissions_and_nonspoken_modalities_require_manual_task_policy_before_mor_gra_reference_use"
)
REVIEW_STATUS = "separate_task_candidate_requires_access"
RECOMMENDED_NEXT_ACTION = (
    "Keep AAC out of toyplay Reference Cohorts; require project-owner access confirmation "
    "and separate aac_intervention task policy before any intake."
)

REVIEW_COLUMNS = [
    "corpus",
    "official_url",
    "official_participant_count",
    "official_video_subset_count",
    "access_requirement",
    "age_eligibility_raw",
    "collection_context",
    "task_fit_for_toyplay",
    "recommended_task_type",
    "mor_gra_warning",
    "review_status",
    "recommended_next_action",
]


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=REVIEW_COLUMNS, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in REVIEW_COLUMNS})


def build_aac_review_row(
    *,
    official_url: str = OFFICIAL_URL,
    official_participant_count: int = OFFICIAL_PARTICIPANT_COUNT,
    official_video_subset_count: int = OFFICIAL_VIDEO_SUBSET_COUNT,
    access_requirement: str = ACCESS_REQUIREMENT,
    age_eligibility_raw: str = AGE_ELIGIBILITY_RAW,
    collection_context: str = COLLECTION_CONTEXT,
    task_fit_for_toyplay: str = TASK_FIT_FOR_TOYPLAY,
    recommended_task_type: str = RECOMMENDED_TASK_TYPE,
    mor_gra_warning: str = MOR_GRA_WARNING,
) -> dict[str, object]:
    return {
        "corpus": CORPUS,
        "official_url": official_url,
        "official_participant_count": official_participant_count,
        "official_video_subset_count": official_video_subset_count,
        "access_requirement": access_requirement,
        "age_eligibility_raw": age_eligibility_raw,
        "collection_context": collection_context,
        "task_fit_for_toyplay": task_fit_for_toyplay,
        "recommended_task_type": recommended_task_type,
        "mor_gra_warning": mor_gra_warning,
        "review_status": REVIEW_STATUS,
        "recommended_next_action": RECOMMENDED_NEXT_ACTION,
    }


def write_aac_review(
    *,
    output_path: Path = OUTPUT_PATH,
    official_url: str = OFFICIAL_URL,
    official_participant_count: int = OFFICIAL_PARTICIPANT_COUNT,
    official_video_subset_count: int = OFFICIAL_VIDEO_SUBSET_COUNT,
    access_requirement: str = ACCESS_REQUIREMENT,
    age_eligibility_raw: str = AGE_ELIGIBILITY_RAW,
    collection_context: str = COLLECTION_CONTEXT,
    task_fit_for_toyplay: str = TASK_FIT_FOR_TOYPLAY,
    recommended_task_type: str = RECOMMENDED_TASK_TYPE,
    mor_gra_warning: str = MOR_GRA_WARNING,
) -> list[dict[str, object]]:
    row = build_aac_review_row(
        official_url=official_url,
        official_participant_count=official_participant_count,
        official_video_subset_count=official_video_subset_count,
        access_requirement=access_requirement,
        age_eligibility_raw=age_eligibility_raw,
        collection_context=collection_context,
        task_fit_for_toyplay=task_fit_for_toyplay,
        recommended_task_type=recommended_task_type,
        mor_gra_warning=mor_gra_warning,
    )
    rows = [row]
    _write_csv(output_path, rows)
    return rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    parser.add_argument("--official-url", default=OFFICIAL_URL)
    parser.add_argument("--official-participant-count", type=int, default=OFFICIAL_PARTICIPANT_COUNT)
    parser.add_argument("--official-video-subset-count", type=int, default=OFFICIAL_VIDEO_SUBSET_COUNT)
    parser.add_argument("--access-requirement", default=ACCESS_REQUIREMENT)
    parser.add_argument("--age-eligibility-raw", default=AGE_ELIGIBILITY_RAW)
    parser.add_argument("--collection-context", default=COLLECTION_CONTEXT)
    parser.add_argument("--task-fit-for-toyplay", default=TASK_FIT_FOR_TOYPLAY)
    parser.add_argument("--recommended-task-type", default=RECOMMENDED_TASK_TYPE)
    parser.add_argument("--mor-gra-warning", default=MOR_GRA_WARNING)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rows = write_aac_review(
        output_path=args.output,
        official_url=args.official_url,
        official_participant_count=args.official_participant_count,
        official_video_subset_count=args.official_video_subset_count,
        access_requirement=args.access_requirement,
        age_eligibility_raw=args.age_eligibility_raw,
        collection_context=args.collection_context,
        task_fit_for_toyplay=args.task_fit_for_toyplay,
        recommended_task_type=args.recommended_task_type,
        mor_gra_warning=args.mor_gra_warning,
    )
    print(f"Saved: {args.output} ({len(rows)} row)")
    print(f"review_status: {rows[0]['review_status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

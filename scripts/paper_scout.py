"""On-demand literature scout for ASD decision-support research."""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SEED_PATH = PROJECT_ROOT / "docs" / "literature" / "consensus_papers_2026-04-26.csv"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "docs" / "literature" / "scout_reports"
SEMANTIC_SCHOLAR_ENDPOINT = "https://api.semanticscholar.org/graph/v1/paper/search"
OPENALEX_ENDPOINT = "https://api.openalex.org/works"
DEFAULT_TAGS = [
    "speech",
    "audio",
    "language",
    "video",
    "behavior",
    "questionnaire",
    "multimodal",
    "clinical-validation",
    "ethics",
    "privacy",
    "Thai/local-context",
]


@dataclass(frozen=True)
class PaperCandidate:
    title: str
    year: int | None = None
    authors: tuple[str, ...] = ()
    abstract: str = ""
    venue: str = ""
    doi: str = ""
    url: str = ""
    citation_count: int | None = None
    source_query: str = ""


def normalize_title(title: str) -> str:
    text = title.lower().strip()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def normalize_doi(doi: str) -> str:
    doi = doi.strip().lower()
    doi = doi.removeprefix("https://doi.org/")
    doi = doi.removeprefix("http://doi.org/")
    doi = doi.removeprefix("doi:")
    return doi.strip()


def load_seed_keys(seed_path: Path = DEFAULT_SEED_PATH) -> tuple[set[str], set[str]]:
    titles: set[str] = set()
    dois: set[str] = set()
    if not seed_path.exists():
        return titles, dois

    with seed_path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            title = normalize_title(row.get("Title", ""))
            doi = normalize_doi(row.get("DOI", ""))
            if title:
                titles.add(title)
            if doi:
                dois.add(doi)
    return titles, dois


def build_search_queries(tags: Iterable[str] | None = None, custom_query: str | None = None) -> list[str]:
    if custom_query:
        return [custom_query]

    selected = {tag.lower() for tag in (tags or []) if tag}
    base = '"autism spectrum disorder" "artificial intelligence" assessment screening'
    queries = [
        base,
        '"autism spectrum disorder" "machine learning" speech language assessment',
        '"autism spectrum disorder" speech audio acoustic machine learning',
        '"autism spectrum disorder" video behavior machine learning screening',
        '"autism spectrum disorder" questionnaire clinical validation AI screening',
        '"autism spectrum disorder" multimodal artificial intelligence diagnosis support',
        '"autism spectrum disorder" AI privacy ethics clinical implementation',
        '"autism spectrum disorder" Thai language machine learning screening',
    ]

    tag_queries = {
        "speech": '"autism spectrum disorder" speech machine learning assessment',
        "audio": '"autism spectrum disorder" audio acoustic deep learning screening',
        "language": '"autism spectrum disorder" language NLP machine learning assessment',
        "video": '"autism spectrum disorder" video behavior machine learning screening',
        "behavior": '"autism spectrum disorder" behavior observation AI screening',
        "questionnaire": '"autism spectrum disorder" questionnaire machine learning screening',
        "multimodal": '"autism spectrum disorder" multimodal AI diagnosis support',
        "clinical-validation": '"autism spectrum disorder" AI clinical validation assessment',
        "ethics": '"autism spectrum disorder" artificial intelligence ethics privacy',
        "privacy": '"autism spectrum disorder" AI privacy consent clinical',
        "thai/local-context": '"autism spectrum disorder" Thai language screening machine learning',
        "thai": '"autism spectrum disorder" Thai language screening machine learning',
    }
    if selected:
        queries = [tag_queries[tag] for tag in selected if tag in tag_queries] or queries

    seen: set[str] = set()
    unique_queries: list[str] = []
    for query in queries:
        if query not in seen:
            unique_queries.append(query)
            seen.add(query)
    return unique_queries


def fetch_semantic_scholar(
    query: str,
    *,
    year_from: int,
    year_to: int,
    limit: int,
    timeout: int = 20,
) -> list[PaperCandidate]:
    fields = ",".join([
        "title",
        "year",
        "authors",
        "abstract",
        "venue",
        "externalIds",
        "url",
        "citationCount",
    ])
    params = urlencode({
        "query": query,
        "year": f"{year_from}-{year_to}",
        "limit": min(max(limit, 1), 100),
        "fields": fields,
    })
    request = Request(
        f"{SEMANTIC_SCHOLAR_ENDPOINT}?{params}",
        headers={
            "User-Agent": "asd-project-paper-scout/1.0",
            **({"x-api-key": os.environ["S2_API_KEY"]} if os.environ.get("S2_API_KEY") else {}),
        },
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise RuntimeError(f"Semantic Scholar request failed ({exc.code}) for query: {query}") from exc
    except URLError as exc:
        raise RuntimeError(f"Semantic Scholar request failed for query: {query}: {exc.reason}") from exc

    candidates: list[PaperCandidate] = []
    for item in payload.get("data", []):
        external_ids = item.get("externalIds") or {}
        authors = tuple(author.get("name", "") for author in item.get("authors", []) if author.get("name"))
        candidates.append(
            PaperCandidate(
                title=item.get("title") or "not reported",
                year=item.get("year"),
                authors=authors,
                abstract=item.get("abstract") or "",
                venue=item.get("venue") or "not reported",
                doi=external_ids.get("DOI") or "",
                url=item.get("url") or "",
                citation_count=item.get("citationCount"),
                source_query=query,
            )
        )
    return candidates


def restore_openalex_abstract(inverted_index: dict[str, list[int]] | None) -> str:
    if not inverted_index:
        return ""
    positioned: list[tuple[int, str]] = []
    for word, positions in inverted_index.items():
        positioned.extend((position, word) for position in positions)
    return " ".join(word for _, word in sorted(positioned))


def fetch_openalex(
    query: str,
    *,
    year_from: int,
    year_to: int,
    limit: int,
    timeout: int = 20,
) -> list[PaperCandidate]:
    params = {
        "search": query,
        "filter": f"from_publication_date:{year_from}-01-01,to_publication_date:{year_to}-12-31,is_retracted:false",
        "per_page": min(max(limit, 1), 100),
    }
    if os.environ.get("OPENALEX_API_KEY"):
        params["api_key"] = os.environ["OPENALEX_API_KEY"]
    if os.environ.get("OPENALEX_MAILTO"):
        params["mailto"] = os.environ["OPENALEX_MAILTO"]

    request = Request(
        f"{OPENALEX_ENDPOINT}?{urlencode(params)}",
        headers={"User-Agent": "asd-project-paper-scout/1.0"},
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise RuntimeError(f"OpenAlex request failed ({exc.code}) for query: {query}") from exc
    except URLError as exc:
        raise RuntimeError(f"OpenAlex request failed for query: {query}: {exc.reason}") from exc

    candidates: list[PaperCandidate] = []
    for item in payload.get("results", []):
        primary_location = item.get("primary_location") or {}
        source = primary_location.get("source") or {}
        authors = tuple(
            authorship.get("author", {}).get("display_name", "")
            for authorship in item.get("authorships", [])
            if authorship.get("author", {}).get("display_name")
        )
        candidates.append(
            PaperCandidate(
                title=item.get("display_name") or item.get("title") or "not reported",
                year=item.get("publication_year"),
                authors=authors,
                abstract=restore_openalex_abstract(item.get("abstract_inverted_index")),
                venue=source.get("display_name") or "not reported",
                doi=item.get("doi") or "",
                url=primary_location.get("landing_page_url") or item.get("id") or "",
                citation_count=item.get("cited_by_count"),
                source_query=query,
            )
        )
    return candidates


def fetch_candidates(
    query: str,
    *,
    year_from: int,
    year_to: int,
    limit: int,
    backend: str,
) -> tuple[list[PaperCandidate], list[str]]:
    warnings: list[str] = []
    if backend in {"semantic-scholar", "auto"}:
        try:
            return (
                fetch_semantic_scholar(query, year_from=year_from, year_to=year_to, limit=limit),
                warnings,
            )
        except RuntimeError as exc:
            warnings.append(str(exc))
            if backend == "semantic-scholar":
                return [], warnings

    if backend in {"openalex", "auto"}:
        try:
            return fetch_openalex(query, year_from=year_from, year_to=year_to, limit=limit), warnings
        except RuntimeError as exc:
            warnings.append(str(exc))
    return [], warnings


def text_blob(candidate: PaperCandidate) -> str:
    return f"{candidate.title} {candidate.abstract} {candidate.venue}".lower()


def infer_tags(candidate: PaperCandidate) -> list[str]:
    blob = text_blob(candidate)
    tag_patterns = {
        "speech": ["speech", "spoken", "vocal", "vocalization", "prosody"],
        "audio": ["audio", "acoustic", "voice", "sound"],
        "language": ["language", "linguistic", "narrative", "text", "nlp", "communication"],
        "video": ["video", "facial", "face", "gaze", "eye-tracking", "home video"],
        "behavior": ["behavior", "behaviour", "gesture", "motion", "social"],
        "questionnaire": ["questionnaire", "checklist", "parent-report", "survey", "m-chat"],
        "multimodal": ["multimodal", "multi-modal", "multi modular", "multi-modular"],
        "clinical-validation": ["clinical", "validation", "prospective", "sensitivity", "specificity", "auc"],
        "ethics": ["ethic", "bias", "fairness", "explainability", "explainable"],
        "privacy": ["privacy", "consent", "security", "data protection"],
        "Thai/local-context": ["thai", "thailand", "local context", "low-resource"],
    }
    tags = [tag for tag, patterns in tag_patterns.items() if any(pattern in blob for pattern in patterns)]
    return tags or ["not reported"]


def screen_candidate(candidate: PaperCandidate) -> tuple[str, str]:
    blob = text_blob(candidate)
    has_asd = any(term in blob for term in ["autism", "asd", "autism spectrum disorder"])
    has_ai = any(
        term in blob
        for term in [
            "artificial intelligence",
            "machine learning",
            "deep learning",
            "neural",
            "classification",
            "model",
            "algorithm",
            "nlp",
        ]
    )
    has_assessment_task = any(
        term in blob
        for term in [
            "screening",
            "assessment",
            "diagnosis",
            "diagnostic",
            "detection",
            "classification",
            "severity",
        ]
    )
    tags = set(infer_tags(candidate))
    has_modality = bool(tags - {"clinical-validation", "ethics", "privacy", "not reported"})

    if has_asd and has_ai and has_assessment_task and has_modality:
        return "include", "ตรงกับ ASD + AI/ML + งานคัดกรอง/ประเมิน และมี modality ที่เกี่ยวกับโปรเจกต์"
    if has_asd and has_ai and (has_assessment_task or has_modality):
        return "maybe", "เกี่ยวข้องกับ ASD และ AI แต่ต้องอ่าน abstract/full text เพื่อยืนยัน scope และหลักฐาน"
    return "exclude", "ยังไม่พบองค์ประกอบหลักครบถ้วนจาก metadata ที่ดึงได้"


def dedupe_candidates(
    candidates: Iterable[PaperCandidate],
    seed_titles: set[str],
    seed_dois: set[str],
) -> list[PaperCandidate]:
    seen_titles = set(seed_titles)
    seen_dois = set(seed_dois)
    unique: list[PaperCandidate] = []
    for candidate in candidates:
        title_key = normalize_title(candidate.title)
        doi_key = normalize_doi(candidate.doi)
        if title_key and title_key in seen_titles:
            continue
        if doi_key and doi_key in seen_dois:
            continue
        if title_key:
            seen_titles.add(title_key)
        if doi_key:
            seen_dois.add(doi_key)
        unique.append(candidate)
    return unique


def rank_candidates(candidates: Iterable[PaperCandidate]) -> list[PaperCandidate]:
    decision_weight = {"include": 2, "maybe": 1, "exclude": 0}

    def score(candidate: PaperCandidate) -> tuple[int, int, int]:
        decision, _ = screen_candidate(candidate)
        tag_count = len([tag for tag in infer_tags(candidate) if tag != "not reported"])
        citations = candidate.citation_count or 0
        return (decision_weight[decision], tag_count, citations)

    return sorted(candidates, key=score, reverse=True)


def format_markdown_report(
    candidates: list[PaperCandidate],
    *,
    search_terms: list[str],
    limit: int,
    seed_path: Path,
    generated_at: datetime | None = None,
) -> str:
    generated_at = generated_at or datetime.now()
    selected = candidates[:limit]
    lines = [
        "# On-Demand ASD Literature Paper Scout",
        "",
        f"Generated: {generated_at.strftime('%Y-%m-%d %H:%M')}",
        f"Seed list: `{seed_path}`",
        "",
        "## Search Terms Used",
        "",
    ]
    lines.extend(f"- {term}" for term in search_terms)
    lines.extend(["", "## New Candidate Papers", ""])
    if not selected:
        lines.append("No new candidate papers found. Try a narrower tag or rerun later.")
    for index, candidate in enumerate(selected, start=1):
        decision, reason = screen_candidate(candidate)
        tags = ", ".join(infer_tags(candidate))
        authors = ", ".join(candidate.authors[:3]) if candidate.authors else "not reported"
        if len(candidate.authors) > 3:
            authors += ", et al."
        doi = normalize_doi(candidate.doi) or "not reported"
        url = candidate.url or (f"https://doi.org/{doi}" if doi != "not reported" else "not reported")
        citations = candidate.citation_count if candidate.citation_count is not None else "not reported"
        abstract_note = candidate.abstract.strip()
        if len(abstract_note) > 420:
            abstract_note = f"{abstract_note[:417].rstrip()}..."
        abstract_note = abstract_note or "not reported"
        lines.extend([
            f"### {index}. {candidate.title}",
            "",
            f"- Year: {candidate.year or 'not reported'}",
            f"- Authors: {authors}",
            f"- Venue: {candidate.venue or 'not reported'}",
            f"- DOI/link: {doi} | {url}",
            f"- Citations: {citations}",
            f"- Suggested tag: {tags}",
            f"- Screening decision: {decision} — {reason}",
            f"- Why relevant: {why_relevant(candidate)}",
            f"- Findings from paper metadata: {abstract_note}",
            f"- AI interpretation: ควรใช้เป็นหลักฐาน decision-support เท่านั้น จนกว่าจะอ่าน full text และตรวจ method/dataset/metric",
            "",
        ])
    lines.extend(["## Next Action", "", next_action(selected)])
    return "\n".join(lines).strip() + "\n"


def why_relevant(candidate: PaperCandidate) -> str:
    tags = set(infer_tags(candidate))
    if "speech" in tags or "audio" in tags or "language" in tags:
        return "ใกล้กับแกนโปรเจกต์ด้าน speech/language features สำหรับ speech therapist"
    if "video" in tags or "behavior" in tags:
        return "ช่วยเติมมุม video/behavioral observation สำหรับ future multimodal workflow"
    if "questionnaire" in tags or "multimodal" in tags:
        return "เกี่ยวกับการรวมข้อมูลหลายแหล่งหรือ screening workflow ที่อาจเทียบกับระบบของโปรเจกต์ได้"
    if "clinical-validation" in tags:
        return "ช่วยประเมินระดับหลักฐานและข้อจำกัดก่อนนำไปอ้างใน clinical decision-support context"
    if "ethics" in tags or "privacy" in tags:
        return "ช่วยเสริม safety boundary, consent, privacy, bias และ human-in-the-loop framing"
    return "เกี่ยวข้องเชิงกว้าง แต่ต้องอ่าน abstract/full text เพื่อยืนยัน relevance"


def next_action(candidates: list[PaperCandidate]) -> str:
    includes = [candidate for candidate in candidates if screen_candidate(candidate)[0] == "include"]
    maybes = [candidate for candidate in candidates if screen_candidate(candidate)[0] == "maybe"]
    priority = includes or maybes
    if not priority:
        return "ยังไม่มี paper ที่ควรอ่านต่อทันที รอบถัดไปให้ลอง `--tag speech` หรือ `--tag video` เพื่อบีบ scope."
    titles = [f"`{candidate.title}`" for candidate in priority[:3]]
    return "อ่าน abstract/full text ก่อนสำหรับ " + ", ".join(titles) + " แล้วค่อยเพิ่มเข้า Zotero หรือ literature matrix."


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Find and screen new ASD AI literature on demand.")
    parser.add_argument("--tag", action="append", default=[], help="Focus tag, e.g. speech, video, multimodal.")
    parser.add_argument("--query", help="Custom search query. Overrides built-in query set.")
    parser.add_argument("--limit", type=int, default=10, help="Number of candidates to show.")
    parser.add_argument("--per-query", type=int, default=10, help="Semantic Scholar results fetched per query.")
    parser.add_argument("--year-from", type=int, default=2020)
    parser.add_argument("--year-to", type=int, default=2026)
    parser.add_argument("--seed", type=Path, default=DEFAULT_SEED_PATH)
    parser.add_argument("--save", action="store_true", help="Save the Markdown report under docs/literature/scout_reports.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--sleep", type=float, default=1.0, help="Seconds to wait between API requests.")
    parser.add_argument(
        "--backend",
        choices=["auto", "semantic-scholar", "openalex"],
        default="auto",
        help="Metadata API backend. Auto uses Semantic Scholar first, then OpenAlex fallback.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    search_terms = build_search_queries(args.tag, args.query)
    seed_titles, seed_dois = load_seed_keys(args.seed)
    all_candidates: list[PaperCandidate] = []

    errors: list[str] = []
    for index, query in enumerate(search_terms):
        candidates, warnings = fetch_candidates(
            query,
            year_from=args.year_from,
            year_to=args.year_to,
            limit=args.per_query,
            backend=args.backend,
        )
        all_candidates.extend(candidates)
        errors.extend(warnings)
        if index < len(search_terms) - 1 and args.sleep > 0:
            time.sleep(args.sleep)

    unique = dedupe_candidates(all_candidates, seed_titles, seed_dois)
    ranked = rank_candidates(unique)
    report = format_markdown_report(
        ranked,
        search_terms=search_terms,
        limit=args.limit,
        seed_path=args.seed,
    )
    if errors:
        report += "\n## Fetch Warnings\n\n" + "\n".join(f"- {error}" for error in errors) + "\n"
    print(report)

    if args.save:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        out_path = args.output_dir / f"paper_scout_{datetime.now().strftime('%Y-%m-%d_%H%M')}.md"
        out_path.write_text(report, encoding="utf-8")
        print(f"\n[saved] {out_path.relative_to(PROJECT_ROOT)}")
    return 0 if ranked or errors else 1


if __name__ == "__main__":
    raise SystemExit(main())

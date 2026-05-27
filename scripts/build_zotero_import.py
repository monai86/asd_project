"""Build Zotero-ready RIS files from the literature scout outputs."""

from __future__ import annotations

import csv
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SEED_CSV = PROJECT_ROOT / "docs" / "literature" / "consensus_papers_2026-04-26.csv"
SCOUT_REPORT = PROJECT_ROOT / "docs" / "literature" / "scout_reports" / "paper_scout_2026-05-23_1525.md"
OUTPUT_DIR = PROJECT_ROOT / "docs" / "literature" / "zotero_import"
CLEAN_OUTPUT_DIR = PROJECT_ROOT / "docs" / "literature" / "zotero_import_clean"

COLLECTIONS = {
    "01_Speech_Audio": {"speech", "audio"},
    "02_Language_Text": {"language", "nlp", "text", "transcript"},
    "03_Video_Behavior": {"video", "behavior"},
    "04_Questionnaire_Screening": {"questionnaire", "screening"},
    "05_Multimodal_AI": {"multimodal"},
    "06_Clinical_Ethics_Privacy": {"clinical-validation", "ethics", "privacy"},
    "07_Review_Papers": {"review"},
    "08_Maybe_Exclude_Check": {"maybe", "exclude", "not-reported"},
    "09_Thai_Local_Context": {"Thai-local-context", "Thailand", "Thai-language", "Thai-affiliation"},
}

EXTRA_RECORDS = [
    {
        "title": "Machine Learning-Based Early Prediction Model for Autism Spectrum Disorder in Infants Using Acoustic Feature",
        "year": "2026",
        "authors": "Shengjian Yin; Zhijia Li; Luyang Guan; Zenghe Yue; Jincen Wang; Jinyi Zhu; Yazhu Han; Qian Li; Lan Lin; Yaxin Dai; Haozhen Chen; Yuheng Chen; Yun Li; Xiaoyan Ke",
        "journal": "Autism Research",
        "doi": "10.1002/aur.70179",
        "url": "https://pubmed.ncbi.nlm.nih.gov/41502369/",
        "tags": "ASD, speech, audio, acoustic, machine-learning, screening, PubMed, priority",
        "notes": "PubMed shortlist. Verify full text before using numeric performance claims.",
    },
    {
        "title": "Vocal markers of autism: Assessing the generalizability of machine learning models",
        "year": "2022",
        "authors": "",
        "journal": "Autism Research",
        "doi": "10.1002/aur.2721",
        "url": "https://pubmed.ncbi.nlm.nih.gov/35385224/",
        "tags": "ASD, speech, audio, vocal-markers, machine-learning, generalizability, PubMed, priority",
        "notes": "PubMed shortlist. Add complete author metadata from Zotero lookup.",
    },
    {
        "title": "Can Natural Speech Prosody Distinguish Autism Spectrum Disorders? A Meta-Analysis",
        "year": "2024",
        "authors": "Wen Ma; Lele Xu; Hao Zhang; Shurui Zhang",
        "journal": "Behavioral Sciences",
        "doi": "10.3390/bs14020090",
        "url": "https://pubmed.ncbi.nlm.nih.gov/38392443/",
        "tags": "ASD, speech, audio, prosody, machine-learning, review, meta-analysis, PubMed, priority",
        "notes": "Useful for speech/acoustic rationale and limitations.",
    },
    {
        "title": "Multimodal AI for risk stratification in autism spectrum disorder: integrating voice and screening tools",
        "year": "2025",
        "authors": "",
        "journal": "NPJ Digital Medicine",
        "doi": "10.1038/s41746-025-01914-6",
        "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC12370947/",
        "tags": "ASD, speech, audio, questionnaire, multimodal, clinical-validation, machine-learning, PubMed, priority",
        "notes": "Strong match for voice plus screening-tool workflow. Complete authors via Zotero lookup.",
    },
    {
        "title": "Automatic Identification of High-Risk Autism Spectrum Disorder: A Feasibility Study Using Video and Audio Data Under the Still-Face Paradigm",
        "year": "2020",
        "authors": "",
        "journal": "IEEE Transactions on Neural Systems and Rehabilitation Engineering",
        "doi": "10.1109/TNSRE.2020.3027756",
        "url": "https://pubmed.ncbi.nlm.nih.gov/32991285/",
        "tags": "ASD, video, audio, behavior, machine-learning, screening, PubMed, IEEE, priority",
        "notes": "Good bridge between video and audio modalities.",
    },
    {
        "title": "Early diagnostic value of home video-based machine learning in autism spectrum disorder: a meta-analysis",
        "year": "2024",
        "authors": "",
        "journal": "",
        "doi": "",
        "url": "https://pubmed.ncbi.nlm.nih.gov/39567383/",
        "tags": "ASD, video, behavior, home-video, machine-learning, review, meta-analysis, PubMed, priority",
        "notes": "Complete DOI/authors via Zotero lookup from PMID.",
    },
    {
        "title": "Computational Methods to Measure Patterns of Gaze in Toddlers With Autism Spectrum Disorder",
        "year": "2021",
        "authors": "",
        "journal": "",
        "doi": "",
        "url": "https://pubmed.ncbi.nlm.nih.gov/33900383/",
        "tags": "ASD, video, behavior, gaze, screening, clinical-validation, PubMed, priority",
        "notes": "Gaze/video screening candidate. Complete DOI/authors via Zotero lookup.",
    },
    {
        "title": "Deep learning based approach for Behavior classification in diagnoses of Autism Spectrum Disorder using naturalistic videos",
        "year": "2026",
        "authors": "",
        "journal": "Frontiers in Computational Neuroscience",
        "doi": "10.3389/fncom.2026.1626315",
        "url": "https://pubmed.ncbi.nlm.nih.gov/41929585/",
        "tags": "ASD, video, behavior, deep-learning, screening, PubMed, priority",
        "notes": "Recent naturalistic-video candidate.",
    },
    {
        "title": "Transparent deep learning to identify autism spectrum disorders (ASD) in EHR using clinical notes",
        "year": "2024",
        "authors": "",
        "journal": "Journal of the American Medical Informatics Association",
        "doi": "",
        "url": "https://pubmed.ncbi.nlm.nih.gov/38626184/",
        "tags": "ASD, language, nlp, clinical-notes, deep-learning, ethics, explainability, PubMed",
        "notes": "Useful for NLP and transparent clinical decision-support framing.",
    },
    {
        "title": "Validation of a Mobile App for Remote Autism Screening in Toddlers",
        "year": "2024",
        "authors": "",
        "journal": "NEJM AI",
        "doi": "",
        "url": "https://pubmed.ncbi.nlm.nih.gov/40438470/",
        "tags": "ASD, screening, questionnaire, video, mobile-app, clinical-validation, PubMed",
        "notes": "Remote/mobile screening candidate. Complete DOI/authors via Zotero lookup.",
    },
    {
        "title": "Sensing technologies and machine learning methods for emotion recognition in autism: Systematic review",
        "year": "2024",
        "authors": "",
        "journal": "International Journal of Medical Informatics",
        "doi": "10.1016/j.ijmedinf.2024.105469",
        "url": "https://pubmed.ncbi.nlm.nih.gov/38723429/",
        "tags": "ASD, video, behavior, sensing, machine-learning, review, ethics, PubMed",
        "notes": "Good for behavioral sensing and ethics limitations.",
    },
    {
        "title": "Machine Learning Prediction of Autism Spectrum Disorder From a Minimal Set of Medical and Background Information",
        "year": "2024",
        "authors": "",
        "journal": "JAMA Network Open",
        "doi": "",
        "url": "https://pubmed.ncbi.nlm.nih.gov/39158907/",
        "tags": "ASD, screening, machine-learning, clinical-validation, PubMed",
        "notes": "Lightweight clinical screening comparison paper.",
    },
    {
        "title": "Artificial Intelligence and the Future of Communication Sciences and Disorders: A Bibliometric and Visualization Analysis",
        "year": "2024",
        "authors": "",
        "journal": "Journal of Speech, Language, and Hearing Research",
        "doi": "10.1044/2024_JSLHR-24-00157",
        "url": "https://pubmed.ncbi.nlm.nih.gov/39418583/",
        "tags": "speech, language, communication-sciences, review, bibliometric, PubMed, priority",
        "notes": "Useful for speech-language pathology context.",
    },
    {
        "title": "Screening autism spectrum disorder in children using machine learning on speech transcripts",
        "year": "2025",
        "authors": "",
        "journal": "Scientific Reports",
        "doi": "10.1038/s41598-025-01500-6",
        "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC12489003/",
        "tags": "ASD, speech, language, transcript, machine-learning, screening, Google-Scholar-style, priority",
        "notes": "Very close to TalkBank/CHAT transcript workflow.",
    },
    {
        "title": "The Noor Project: fair transformer transfer learning for autism spectrum disorder recognition from speech",
        "year": "2025",
        "authors": "",
        "journal": "",
        "doi": "",
        "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC12399525/",
        "tags": "ASD, speech, audio, transformer, fairness, machine-learning, Google-Scholar-style, priority",
        "notes": "Use for fairness/bias discussion in speech models.",
    },
    {
        "title": "Automated detection of adult autism from vowel acoustics using machine learning",
        "year": "2026",
        "authors": "Georgios P. Georgiou; Maria Paphiti",
        "journal": "medRxiv",
        "doi": "10.64898/2026.04.03.26350102",
        "url": "https://www.medrxiv.org/content/10.64898/2026.04.03.26350102v1",
        "tags": "ASD, speech, audio, acoustic, machine-learning, explainability, preprint, Google-Scholar-style",
        "notes": "Preprint only; do not use as primary evidence until peer reviewed.",
    },
    {
        "title": "Detecting Autism Spectrum Disorder from Raw Speech in Children using STFT Layered CNN Model",
        "year": "2024",
        "authors": "",
        "journal": "IEEE Conference Publication",
        "doi": "",
        "url": "https://ieeexplore.ieee.org/document/10474705",
        "tags": "ASD, speech, audio, CNN, deep-learning, IEEE, priority",
        "notes": "Strong match for audio pipeline. Complete DOI/authors from IEEE Xplore.",
    },
    {
        "title": "Acoustic Features Characterization of Autism Speech for Automated Detection and Classification",
        "year": "2020",
        "authors": "Abhijit Mohanta; Prerana Mukherjee; Vinay Kumar Mirtal",
        "journal": "National Conference on Communications",
        "doi": "10.1109/NCC48643.2020.9056025",
        "url": "https://dblp.uni-trier.de/rec/html/conf/ncc/MohantaMM20",
        "tags": "ASD, speech, audio, acoustic, machine-learning, IEEE, priority",
        "notes": "Direct acoustic-feature paper.",
    },
    {
        "title": "Machine Learning Based Automated Speech Dialog Analysis Of Autistic Children",
        "year": "2019",
        "authors": "Anjana Wijesinghe; Pradeepa Samarasinghe; Sudarshi Seneviratne; Y Pratheepan; Koliya Pulasinghe",
        "journal": "Proceedings of 2019 11th International Conference on Knowledge and Systems Engineering",
        "doi": "10.1109/KSE.2019.8919266",
        "url": "https://pure.ulster.ac.uk/en/publications/machine-learning-based-automated-speech-dialog-analysis-of-autist/",
        "tags": "ASD, speech, audio, dialogue, machine-learning, IEEE, Scopus, background",
        "notes": "Older than default scope but useful as speech-dialog background.",
    },
    {
        "title": "Machine Learning Predictive Models for Autism Spectrum Disorder Using Eye-Tracking Technology",
        "year": "2025",
        "authors": "",
        "journal": "IEEE Conference Publication",
        "doi": "",
        "url": "https://ieeexplore.ieee.org/document/10922037",
        "tags": "ASD, video, behavior, eye-tracking, machine-learning, IEEE",
        "notes": "Future multimodal/video theme.",
    },
    {
        "title": "Development and psychometric evaluation of a Thai Diagnostic Autism Scale for the early diagnosis of Autism Spectrum Disorder",
        "year": "2022",
        "authors": "Duangkamol Tangviriyapaiboon; Samai Sirithongthaworn; Hataichanok Apikomonkon; Patrinee Traisathit",
        "journal": "Autism Research",
        "doi": "10.1002/aur.2631",
        "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC9297913/",
        "tags": "ASD, Thai-local-context, Thailand, questionnaire, screening, clinical-validation, diagnostic-tool, TDAS, priority",
        "notes": "Thai clinical validation paper. Not AI, but important for Thai diagnostic context and local validation framing.",
    },
    {
        "title": "Economic Evaluation of the Thai Diagnostic Autism Scale for Autism Spectrum Disorder Diagnosis in Children Aged 1-5 Years Old",
        "year": "2024",
        "authors": "Duangkamol Tangviriyapaiboon; Unchalee Permsuwan; Chosita Pavasuthipaisit; Athithan Sriminipun; Piyameth Dilokthornsakul",
        "journal": "Healthcare",
        "doi": "10.3390/healthcare12070782",
        "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC11012028/",
        "tags": "ASD, Thai-local-context, Thailand, questionnaire, screening, clinical-validation, diagnostic-tool, economic-evaluation, TDAS, priority",
        "notes": "Thai Diagnostic Autism Scale economic evaluation. Useful for Thai deployment and health-system discussion.",
    },
    {
        "title": "Two-Step Screening of the Modified Checklist for Autism in Toddlers in Thai Children with Language Delay and Typically Developing Children",
        "year": "2016",
        "authors": "Pornchada Srisinghasongkram; Chandhita Pruksananonda; Weerasak Chonchaiya",
        "journal": "Journal of Autism and Developmental Disorders",
        "doi": "10.1007/s10803-016-2876-4",
        "url": "https://pubmed.ncbi.nlm.nih.gov/27460003/",
        "tags": "ASD, Thai-local-context, Thailand, questionnaire, screening, clinical-validation, M-CHAT, language-delay, background, priority",
        "notes": "Thai M-CHAT validation. Older than default date range but important for local screening context.",
    },
    {
        "title": "Robust Autism Spectrum Disorder Screening Based on Facial Images (For Disability Diagnosis): A Domain-Adaptive Deep Ensemble Approach",
        "year": "2025",
        "authors": "Mohammad Shafiul Alam; Muhammad Mahbubur Rashid; Ahmad Jazlan; Md Eshrat E Alahi; Mohamed Kchaou; Khalid Ayed B Alharthi",
        "journal": "Diagnostics",
        "doi": "10.3390/diagnostics15131601",
        "url": "https://pubmed.ncbi.nlm.nih.gov/40647600/",
        "tags": "ASD, Thai-local-context, Thai-affiliation, video, behavior, deep-learning, machine-learning, facial-image, clinical-validation",
        "notes": "AI paper with Walailak University affiliation. Uses public facial-image datasets, so treat as Thai-affiliated rather than Thai-child validation data.",
    },
    {
        "title": "Detection of Electroencephalographic Abnormalities and Its Associated Factors among Children with Autism Spectrum Disorder in Thailand",
        "year": "2022",
        "authors": "",
        "journal": "Healthcare",
        "doi": "10.3390/healthcare10101969",
        "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC9601834/",
        "tags": "ASD, Thai-local-context, Thailand, EEG, clinical-validation, Thai-ATEC, background",
        "notes": "Thai clinical cohort. Not speech/AI, but useful for Thai ASD severity and local clinical context.",
    },
    {
        "title": "The effects of positive emotional gesture guidance on speech sound discrimination in Thai children with ASD: A mismatch negativity study",
        "year": "2022",
        "authors": "",
        "journal": "Songklanakarin Journal of Science and Technology",
        "doi": "",
        "url": "https://sjst.psu.ac.th/journal/44-2/28.pdf",
        "tags": "ASD, Thai-local-context, Thailand, speech, audio, language, EEG, mismatch-negativity, background, priority",
        "notes": "Thai children with ASD and speech sound discrimination. Useful local speech-language background, not AI.",
    },
    {
        "title": "Speech and Language in Children with Autism Spectrum Disorders",
        "year": "2023",
        "authors": "",
        "journal": "Siriraj Medical Bulletin",
        "doi": "",
        "url": "https://he02.tci-thaijo.org/index.php/simedbull/article/view/256480",
        "tags": "ASD, Thai-local-context, Thailand, speech, language, clinical-background, background",
        "notes": "Thai clinical speech-language background article.",
    },
    {
        "title": "Translation and validation of the developmental, dimensional and diagnostic interview (3Di) for diagnosis of autism spectrum disorder in Thai children",
        "year": "2011",
        "authors": "",
        "journal": "",
        "doi": "",
        "url": "https://murex.mahidol.ac.th/en/publications/translation-and-validation-of-the-developmental-dimensional-and-d/",
        "tags": "ASD, Thai-local-context, Thailand, questionnaire, screening, clinical-validation, diagnostic-interview, 3Di, background",
        "notes": "Older Thai diagnostic-interview validation. Use as local background if needed.",
    },
]


@dataclass
class Record:
    title: str
    year: str = ""
    authors: list[str] = field(default_factory=list)
    journal: str = ""
    doi: str = ""
    url: str = ""
    abstract: str = ""
    tags: set[str] = field(default_factory=set)
    notes: str = ""
    source: str = ""


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def normalize_title(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()


def split_authors(authors: str) -> list[str]:
    if not authors:
        return []
    if ";" in authors:
        parts = authors.split(";")
    else:
        authors = re.sub(r",\s+et al\.?", "", authors)
        parts = re.split(r"\s+and\s+|,\s+", authors)
    return [clean_text(part) for part in parts if clean_text(part)]


def base_tags() -> set[str]:
    return {"ASD", "machine-learning", "decision-support"}


def infer_tags(text: str, study_type: str = "") -> set[str]:
    blob = f"{text} {study_type}".lower()
    tags = base_tags()
    patterns = {
        "speech": ["speech", "spoken", "vocal", "vocalization", "voice", "prosody"],
        "audio": ["audio", "acoustic", "voice", "sound", "vocal"],
        "language": ["language", "linguistic", "narrative", "communication"],
        "video": ["video", "facial", "face", "gaze", "eye-tracking", "home video"],
        "behavior": ["behavior", "behaviour", "gesture", "motion", "social"],
        "questionnaire": ["questionnaire", "checklist", "parent-report", "m-chat", "survey"],
        "screening": ["screening", "assessment", "detection", "diagnosis support"],
        "multimodal": ["multimodal", "multi-modal", "multi modular", "multi-modular"],
        "clinical-validation": ["clinical", "validation", "prospective", "sensitivity", "specificity", "auc"],
        "ethics": ["ethic", "bias", "fairness", "explainability", "explainable"],
        "privacy": ["privacy", "consent", "secure", "security"],
        "Thai-local-context": ["thai", "thailand", "local context", "low-resource"],
        "review": ["review", "meta-analysis", "scoping review", "systematic"],
    }
    for tag, terms in patterns.items():
        if any(term in blob for term in terms):
            tags.add(tag)
    return tags


def collection_for_tags(tags: set[str], title: str) -> str:
    title_lower = title.lower()
    if COLLECTIONS["09_Thai_Local_Context"] & tags:
        return "09_Thai_Local_Context"
    if "review" in tags or "meta-analysis" in title_lower or "review" in title_lower:
        return "07_Review_Papers"
    if COLLECTIONS["05_Multimodal_AI"] & tags:
        return "05_Multimodal_AI"
    if (COLLECTIONS["06_Clinical_Ethics_Privacy"] & tags) and not (
        COLLECTIONS["01_Speech_Audio"] & tags or COLLECTIONS["03_Video_Behavior"] & tags
    ):
        return "06_Clinical_Ethics_Privacy"
    for name in [
        "01_Speech_Audio",
        "03_Video_Behavior",
        "02_Language_Text",
        "04_Questionnaire_Screening",
        "06_Clinical_Ethics_Privacy",
    ]:
        if COLLECTIONS[name] & tags:
            return name
    return "08_Maybe_Exclude_Check"


def ris_escape(text: str) -> str:
    return clean_text(text).replace("\n", " ")


def record_to_ris(record: Record) -> str:
    lines = ["TY  - JOUR"]
    lines.append(f"TI  - {ris_escape(record.title)}")
    for author in record.authors:
        lines.append(f"AU  - {ris_escape(author)}")
    if record.year:
        lines.append(f"PY  - {ris_escape(record.year)}")
    if record.journal:
        lines.append(f"JO  - {ris_escape(record.journal)}")
    if record.doi:
        lines.append(f"DO  - {ris_escape(record.doi)}")
    if record.url:
        lines.append(f"UR  - {ris_escape(record.url)}")
    if record.abstract:
        lines.append(f"AB  - {ris_escape(record.abstract)}")
    note_parts = [record.notes]
    if record.source:
        note_parts.append(f"Source: {record.source}")
    lines.append(f"N1  - {ris_escape(' | '.join(part for part in note_parts if part))}")
    for tag in sorted(record.tags):
        lines.append(f"KW  - {ris_escape(tag)}")
    lines.append("ER  -")
    return "\n".join(lines) + "\n"


def load_seed_records() -> list[Record]:
    records: list[Record] = []
    with SEED_CSV.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            title = clean_text(row.get("Title", ""))
            abstract = clean_text(row.get("Abstract", ""))
            takeaway = clean_text(row.get("Takeaway", ""))
            study_type = clean_text(row.get("Study Type", ""))
            tags = infer_tags(f"{title} {abstract} {takeaway}", study_type)
            if study_type:
                tags.add(study_type.replace(" ", "-"))
            records.append(
                Record(
                    title=title,
                    year=clean_text(row.get("Year", "")),
                    authors=split_authors(clean_text(row.get("Authors", ""))),
                    journal=clean_text(row.get("Journal", "")),
                    doi=clean_text(row.get("DOI", "")),
                    url=clean_text(row.get("Consensus Link", "")),
                    abstract=abstract,
                    tags=tags,
                    notes=f"Consensus takeaway: {takeaway}" if takeaway else "",
                    source="Consensus seed CSV",
                )
            )
    return records


def parse_scout_report() -> list[Record]:
    text = SCOUT_REPORT.read_text(encoding="utf-8")
    blocks = re.split(r"\n### \d+\. ", text)
    records: list[Record] = []
    for block in blocks[1:]:
        title, _, rest = block.partition("\n")
        fields: dict[str, str] = {}
        for line in rest.splitlines():
            if line.startswith("- ") and ": " in line:
                key, value = line[2:].split(": ", 1)
                fields[key] = value
        doi_link = fields.get("DOI/link", "")
        doi = ""
        url = ""
        if "|" in doi_link:
            doi, url = [clean_text(part) for part in doi_link.split("|", 1)]
            if doi == "not reported":
                doi = ""
            if url == "not reported":
                url = ""
        raw_tags = {
            clean_text(tag)
            for tag in fields.get("Suggested tag", "").split(",")
            if clean_text(tag) and clean_text(tag) != "not reported"
        }
        tags = base_tags() | raw_tags
        decision = fields.get("Screening decision", "").split(" ", 1)[0].strip()
        if decision:
            tags.add(decision)
        records.append(
            Record(
                title=clean_text(title),
                year=clean_text(fields.get("Year", "")),
                authors=split_authors(fields.get("Authors", "")),
                journal=clean_text(fields.get("Venue", "")),
                doi=doi,
                url=url,
                abstract=clean_text(fields.get("Findings from paper metadata", "")),
                tags=tags,
                notes=clean_text(fields.get("Why relevant", "")),
                source="Paper scout report",
            )
        )
    return records


def load_extra_records() -> list[Record]:
    records: list[Record] = []
    for row in EXTRA_RECORDS:
        tags = {clean_text(tag) for tag in row["tags"].split(",") if clean_text(tag)}
        records.append(
            Record(
                title=row["title"],
                year=row["year"],
                authors=split_authors(row["authors"]),
                journal=row["journal"],
                doi=row["doi"],
                url=row["url"],
                tags=base_tags() | tags,
                notes=row["notes"],
                source="Manual PubMed/Google Scholar/IEEE shortlist",
            )
        )
    return records


def dedupe(records: list[Record]) -> list[Record]:
    seen: set[str] = set()
    unique: list[Record] = []
    for record in records:
        key = record.doi.lower().strip() if record.doi else normalize_title(record.title)
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(record)
    return unique


def write_outputs(records: list[Record]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for old_file in OUTPUT_DIR.glob("*.ris"):
        old_file.unlink()
    grouped: dict[str, list[Record]] = defaultdict(list)
    for record in records:
        grouped[collection_for_tags(record.tags, record.title)].append(record)

    all_ris = "".join(record_to_ris(record) + "\n" for record in records)
    (OUTPUT_DIR / "00_All_ASD_AI_Literature.ris").write_text(all_ris, encoding="utf-8")

    for collection_name, collection_records in grouped.items():
        path = OUTPUT_DIR / f"{collection_name}.ris"
        path.write_text("".join(record_to_ris(record) + "\n" for record in collection_records), encoding="utf-8")

    for collection_name in COLLECTIONS:
        if (OUTPUT_DIR / f"{collection_name}.ris").exists():
            continue
        tag_matches = COLLECTIONS[collection_name]
        collection_records = [
            record
            for record in records
            if tag_matches & record.tags
            or (collection_name == "07_Review_Papers" and "review" in record.title.lower())
        ]
        (OUTPUT_DIR / f"{collection_name}.ris").write_text(
            "".join(record_to_ris(record) + "\n" for record in collection_records),
            encoding="utf-8",
        )

    summary_path = OUTPUT_DIR / "zotero_import_summary.csv"
    with summary_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["collection", "title", "year", "doi", "url", "tags", "source"],
        )
        writer.writeheader()
        for record in records:
            writer.writerow({
                "collection": collection_for_tags(record.tags, record.title),
                "title": record.title,
                "year": record.year,
                "doi": record.doi,
                "url": record.url,
                "tags": "; ".join(sorted(record.tags)),
                "source": record.source,
            })

    readme = [
        "# Zotero Import Pack",
        "",
        "Import these RIS files into Zotero one collection at a time.",
        "",
        "Recommended Zotero collection tree:",
        "",
        "```text",
        "AI_ASD_Literature_Review",
        *[f"- {name}" for name in COLLECTIONS],
        "```",
        "",
        "This pack writes RIS files for non-empty primary collections. Use Zotero tags to find cross-cutting groups such as `multimodal`, `ethics`, or `privacy` when those papers are primarily stored under speech/audio or video/behavior.",
        "",
        "Fast path:",
        "",
        "1. Create the parent collection `AI_ASD_Literature_Review` in Zotero.",
        "2. Create subcollections matching the RIS filenames.",
        "3. Select a subcollection, then use `File > Import...` and choose the matching `.ris` file.",
        "4. Keep Zotero's imported tags. They are written as RIS `KW` fields.",
        "5. For items with incomplete metadata, use Zotero's DOI/URL lookup or open the linked PubMed/IEEE/PMC page.",
        "",
        "You can also import `00_All_ASD_AI_Literature.ris` into one collection first, but Zotero will not automatically split it into subcollections.",
        "",
    ]
    (OUTPUT_DIR / "README.md").write_text("\n".join(readme), encoding="utf-8")


def write_clean_outputs(records: list[Record]) -> None:
    CLEAN_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for old_file in CLEAN_OUTPUT_DIR.glob("*.ris"):
        old_file.unlink()

    grouped: dict[str, list[Record]] = defaultdict(list)
    for record in records:
        grouped[collection_for_tags(record.tags, record.title)].append(record)

    for collection_name in COLLECTIONS:
        collection_records = grouped.get(collection_name, [])
        path = CLEAN_OUTPUT_DIR / f"{collection_name}.ris"
        path.write_text(
            "".join(record_to_ris(record) + "\n" for record in collection_records),
            encoding="utf-8",
        )

    summary_path = CLEAN_OUTPUT_DIR / "zotero_import_clean_summary.csv"
    with summary_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["collection", "title", "year", "doi", "url", "tags", "source"],
        )
        writer.writeheader()
        for record in records:
            writer.writerow({
                "collection": collection_for_tags(record.tags, record.title),
                "title": record.title,
                "year": record.year,
                "doi": record.doi,
                "url": record.url,
                "tags": "; ".join(sorted(record.tags)),
                "source": record.source,
            })

    readme = [
        "# Zotero Clean Import Pack",
        "",
        "Use this folder when you want to avoid duplicate Zotero items across collections.",
        "",
        "Important:",
        "",
        "- Import only the `.ris` files in this folder, one subcollection at a time.",
        "- Do not also import `00_All_ASD_AI_Literature.ris` from the older `zotero_import/` folder.",
        "- Each paper appears in exactly one primary collection here.",
        "- Cross-cutting concepts such as `multimodal`, `ethics`, `privacy`, and `Thai-local-context` remain as Zotero tags (`KW` fields).",
        "",
        "Recommended Zotero collection tree:",
        "",
        "```text",
        "AI_ASD_Literature_Review",
        *[f"- {name}" for name in COLLECTIONS],
        "```",
        "",
        "If you already imported duplicates into Zotero, use Zotero's `Duplicate Items` view and merge by DOI/title, or delete the imported collection and re-import from this clean pack.",
        "",
    ]
    (CLEAN_OUTPUT_DIR / "README.md").write_text("\n".join(readme), encoding="utf-8")


def main() -> int:
    records = dedupe(load_seed_records() + parse_scout_report() + load_extra_records())
    write_outputs(records)
    write_clean_outputs(records)
    print(f"Built Zotero import pack with {len(records)} unique records.")
    print(f"Output directory: {OUTPUT_DIR.relative_to(PROJECT_ROOT)}")
    print(f"Clean output directory: {CLEAN_OUTPUT_DIR.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

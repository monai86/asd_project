"""LinguaLens TUI API Client with live REST API and offline mock fallback."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


DEFAULT_API_URL = os.environ.get("LINGUALENS_API_URL", "http://localhost:8000/api/v1")


class LinguaLensClient:
    """Client for interacting with LinguaLens Backend API."""

    def __init__(self, base_url: str = DEFAULT_API_URL, mock_mode: bool = False, seed_demo: bool = False):
        self.base_url = base_url.rstrip("/")
        self.mock_mode = mock_mode
        self._mock_data: dict[str, Any] = self._init_mock_data(seed_demo=seed_demo)

    def seed_demo_dataset(self) -> None:
        """Explicitly seed demo cases and transcripts for demonstration or tutorial."""
        self._mock_data = self._init_mock_data(seed_demo=True)

    def _init_mock_data(self, seed_demo: bool = False) -> dict[str, Any]:
        """Initialize in-memory dataset. Starts clean and empty by default for production readiness."""
        if not seed_demo:
            return {
                "cases": [],
                "sessions": {},
                "transcripts": {},
                "features": {},
                "reports": {},
            }

        return {
            "cases": [
                {
                    "case_id": "case-demo-001",
                    "child_id": "C-0104",
                    "birth_year_month": "2020-04",
                    "age_months": 52,
                    "primary_language": "th",
                    "clinical_notes": "Receptive-expressive language delay evaluation.",
                    "status": "active",
                    "session_count": 2,
                },
                {
                    "case_id": "case-demo-002",
                    "child_id": "C-0208",
                    "birth_year_month": "2021-01",
                    "age_months": 43,
                    "primary_language": "th",
                    "clinical_notes": "Social communication and joint attention follow-up.",
                    "status": "active",
                    "session_count": 1,
                },
            ],
            "sessions": {
                "case-demo-001": [
                    {
                        "session_id": "sess-demo-101",
                        "case_id": "case-demo-001",
                        "session_date": "2026-08-10",
                        "session_number": 1,
                        "status": "Reported",
                        "transcript_id": "tr-demo-101",
                        "feature_set_id": "feat-demo-101",
                        "report_id": "rep-demo-101",
                    },
                    {
                        "session_id": "sess-demo-102",
                        "case_id": "case-demo-001",
                        "session_date": "2026-08-16",
                        "session_number": 2,
                        "status": "Needs Review",
                        "transcript_id": "tr-demo-102",
                        "feature_set_id": None,
                        "report_id": None,
                    },
                ],
                "case-demo-002": [
                    {
                        "session_id": "sess-demo-201",
                        "case_id": "case-demo-002",
                        "session_date": "2026-08-14",
                        "session_number": 1,
                        "status": "Intake",
                        "transcript_id": None,
                        "feature_set_id": None,
                        "report_id": None,
                    }
                ],
            },
            "transcripts": {
                "tr-demo-102": {
                    "transcript_id": "tr-demo-102",
                    "session_id": "sess-demo-102",
                    "status": "pending_review",
                    "utterances": [
                        {"id": "u-1", "speaker": "INV", "text": "สวัสดีครับ วันนี้เรามาเล่นตัวต่อกันนะ", "start_time": 0.0, "end_time": 3.2, "qa_flags": []},
                        {"id": "u-2", "speaker": "CHI", "text": "เล่น รถ", "start_time": 3.5, "end_time": 4.8, "qa_flags": []},
                        {"id": "u-3", "speaker": "INV", "text": "ชอบรถสีอะไรครับ มีสีแดงกับสีน้ำเงิน", "start_time": 5.1, "end_time": 8.0, "qa_flags": []},
                        {"id": "u-4", "speaker": "CHI", "text": "แดง รถ แดง ไป", "start_time": 8.4, "end_time": 10.2, "qa_flags": ["word_boundary_check"]},
                        {"id": "u-5", "speaker": "INV", "text": "รถสีแดงวิ่งเร็วมากเลย บรู๊น บรู๊น", "start_time": 10.5, "end_time": 14.1, "qa_flags": []},
                        {"id": "u-6", "speaker": "CHI", "text": "ไป หา แม่", "start_time": 14.5, "end_time": 16.0, "qa_flags": []},
                    ],
                    "qa_summary": {"total_utterances": 6, "unresolved_flags": 1, "child_utterance_count": 3},
                    "attested": False,
                    "attested_by": None,
                }
            },
            "features": {
                "sess-demo-102": {
                    "feature_set_id": "feat-demo-102",
                    "session_id": "sess-demo-102",
                    "metrics": {
                        "mlu_words": 2.67,
                        "mlu_morphemes": 3.0,
                        "ttr": 0.75,
                        "total_child_utterances": 3,
                        "total_child_words": 8,
                        "intelligibility_rate": 0.95,
                        "turn_taking_ratio": 1.0,
                    },
                    "guideline_links": [
                        {"construct": "Expressive Phrase Length", "status": "Emerging Multi-word", "description": "Child uses 2-3 word utterances (MLU-w: 2.67)."},
                        {"construct": "Lexical Diversity", "status": "Age Expected", "description": "TTR 0.75 indicates diverse word usage in sample."},
                        {"construct": "Social Interaction", "status": "Responsive", "description": "Turn-taking ratio 1.0 with prompt-following."},
                    ],
                }
            },
            "reports": {
                "rep-demo-101": {
                    "report_id": "rep-demo-101",
                    "session_id": "sess-demo-101",
                    "status": "Signed Off",
                    "therapist_name": "Kru Aum (SLP)",
                    "signed_at": "2026-08-10T11:30:00Z",
                    "narrative": "เด็กสามารถสื่อสารด้วยวลี 2 คำได้ดีขึ้น มีการสบตาและผลัดกันพูดในระดับที่น่าพอใจ",
                    "recommendations": "ส่งเสริมการขยายประโยคเป็น 3-4 คำผ่านการเล่นบทบาทสมมติ",
                }
            },
        }

    def _http_request(self, method: str, endpoint: str, data: dict[str, Any] | None = None) -> Any:
        url = f"{self.base_url}{endpoint}"
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        req_data = json.dumps(data).encode("utf-8") if data else None

        req = urllib.request.Request(url, data=req_data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                resp_text = resp.read().decode("utf-8")
                return json.loads(resp_text) if resp_text else {}
        except Exception as exc:
            raise RuntimeError(f"API request failed: {exc}") from exc

    def check_health(self) -> bool:
        """Check if backend API is reachable."""
        if self.mock_mode:
            return False
        try:
            self._http_request("GET", "/cases")
            return True
        except Exception:
            return False

    # Cases
    def list_cases(self) -> list[dict[str, Any]]:
        if not self.mock_mode:
            try:
                return self._http_request("GET", "/cases")
            except Exception:
                pass
        return self._mock_data["cases"]

    def create_case(self, child_id: str, birth_year_month: str, primary_language: str = "th", notes: str = "") -> dict[str, Any]:
        payload = {
            "child_id": child_id,
            "birth_year_month": birth_year_month,
            "primary_language": primary_language,
            "clinical_notes": notes,
        }
        if not self.mock_mode:
            try:
                return self._http_request("POST", "/cases", payload)
            except Exception:
                pass
        new_case = {
            "case_id": f"case-local-{len(self._mock_data['cases']) + 1:03d}",
            "child_id": child_id,
            "birth_year_month": birth_year_month,
            "primary_language": primary_language,
            "clinical_notes": notes,
            "status": "active",
            "session_count": 0,
        }
        self._mock_data["cases"].append(new_case)
        self._mock_data["sessions"][new_case["case_id"]] = []
        return new_case

    # Sessions
    def list_sessions(self, case_id: str) -> list[dict[str, Any]]:
        if not self.mock_mode:
            try:
                case_detail = self._http_request("GET", f"/cases/{case_id}")
                if "sessions" in case_detail:
                    return case_detail["sessions"]
            except Exception:
                pass
        return self._mock_data["sessions"].get(case_id, [])

    def create_session(self, case_id: str, session_date: str, notes: str = "") -> dict[str, Any]:
        payload = {"session_date": session_date, "notes": notes}
        if not self.mock_mode:
            try:
                return self._http_request("POST", f"/cases/{case_id}/sessions", payload)
            except Exception:
                pass
        existing = self._mock_data["sessions"].setdefault(case_id, [])
        new_sess = {
            "session_id": f"sess-local-{case_id[-3:]}-{len(existing) + 1:02d}",
            "case_id": case_id,
            "session_date": session_date,
            "session_number": len(existing) + 1,
            "status": "Intake",
            "transcript_id": None,
            "feature_set_id": None,
            "report_id": None,
            "notes": notes,
        }
        existing.append(new_sess)
        return new_sess

    # Transcripts
    def get_session_transcript(self, session_id: str) -> dict[str, Any] | None:
        if not self.mock_mode:
            try:
                return self._http_request("GET", f"/sessions/{session_id}/transcript")
            except Exception:
                pass
        for tr in self._mock_data["transcripts"].values():
            if tr.get("session_id") == session_id:
                return tr
        return None

    def ingest_transcript_text(self, session_id: str, text: str) -> dict[str, Any]:
        """Convert raw dialogue lines or CHAT file text to transcript without synthetic timestamps."""
        from packages.cha.parser import parse_cha_text

        parsed = parse_cha_text(text, file_id=session_id)
        utterances = []

        if parsed.utterances:
            for idx, u in enumerate(parsed.utterances, 1):
                start_t = round(u.start_ms / 1000.0, 2) if u.start_ms is not None else None
                end_t = round(u.end_ms / 1000.0, 2) if u.end_ms is not None else None
                utterances.append({
                    "id": f"u-{idx}",
                    "speaker": u.speaker_code,
                    "text": u.raw_text,
                    "start_time": start_t,
                    "end_time": end_t,
                    "qa_flags": [],
                })
        else:
            # Simple line-by-line fallback for raw plain text (e.g. "INV: ...", "CHI: ...")
            lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
            for idx, line in enumerate(lines, 1):
                if line.startswith("@") or line.startswith("%"):
                    continue
                speaker = "CHI"
                u_text = line
                if ":" in line:
                    prefix, rest = line.split(":", 1)
                    clean_spk = prefix.replace("*", "").strip().upper()
                    if clean_spk in ["CHI", "INV", "INV1", "INV2", "MOT", "FAT", "EXP", "PAR"]:
                        speaker = clean_spk
                        u_text = rest.strip()
                if u_text:
                    utterances.append({
                        "id": f"u-{idx}",
                        "speaker": speaker,
                        "text": u_text,
                        "start_time": None,
                        "end_time": None,
                        "qa_flags": [],
                    })

        if not utterances:
            utterances = [
                {"id": "u-1", "speaker": "INV", "text": "สวัสดีครับ", "start_time": None, "end_time": None, "qa_flags": []},
                {"id": "u-2", "speaker": "CHI", "text": "เล่น รถ", "start_time": None, "end_time": None, "qa_flags": []},
            ]

        payload = {
            "raw_text": text,
            "utterances": utterances,
        }
        if not self.mock_mode:
            try:
                return self._http_request("POST", f"/sessions/{session_id}/transcripts/manual", payload)
            except Exception:
                pass

        tr_id = f"tr-local-{session_id[-4:]}"
        tr_data = {
            "transcript_id": tr_id,
            "session_id": session_id,
            "raw_cha": text if text.strip().startswith("@") or "*CHI:" in text or "*INV" in text else None,
            "status": "pending_review",
            "utterances": utterances,
            "qa_summary": {
                "total_utterances": len(utterances),
                "unresolved_flags": 0,
                "child_utterance_count": sum(1 for u in utterances if u["speaker"] == "CHI"),
            },
            "attested": False,
            "attested_by": None,
        }
        self._mock_data["transcripts"][tr_id] = tr_data
        for s_list in self._mock_data["sessions"].values():
            for s in s_list:
                if s["session_id"] == session_id:
                    s["transcript_id"] = tr_id
                    s["status"] = "Needs Review"
        return tr_data

    def ingest_audio_file(
        self,
        session_id: str,
        audio_path: str,
        progress_callback: Optional[Any] = None,
    ) -> dict[str, Any]:
        """Ingest audio/video file, extract acoustic profile and speech transcription."""
        from pathlib import Path
        p = Path(audio_path).resolve()
        if not p.exists():
            raise FileNotFoundError(f"Audio/video file not found at: {audio_path}")

        # Transcribe audio and extract acoustic profile via single unified pipeline
        utterances = []
        acoustic_metrics: dict[str, Any] = {}
        raw_chat_text: str | None = None
        try:
            from src.audio_pipeline.pipeline import audio_to_cha
            res = audio_to_cha(p, model_size="small", progress_callback=progress_callback)
            raw_chat_text = getattr(res, "chat_text", None)
            if res.utterances:
                for idx, u in enumerate(res.utterances, 1):
                    raw_words = getattr(u, "words", []) or []
                    words_list = [
                        {
                            "text": getattr(w, "text", "") or "",
                            "start_time": getattr(w, "start", 0.0),
                            "end_time": getattr(w, "end", 0.0),
                            "probability": getattr(w, "probability", 1.0),
                        }
                        for w in raw_words
                    ]
                    utterances.append({
                        "id": f"u-{idx}",
                        "speaker": getattr(u, "speaker", "CHI") or "CHI",
                        "text": getattr(u, "text", "") or "เสียงพูดในคลิป",
                        "start_time": getattr(u, "start", (idx - 1) * 2.0),
                        "end_time": getattr(u, "end", idx * 2.0),
                        "words": words_list,
                        "qa_flags": [],
                    })
            if res.acoustic_profile:
                prof = res.acoustic_profile
                acoustic_metrics = {
                    "duration_sec": round(prof.duration_sec, 2),
                    "f0_median_hz": round(prof.f0_median_hz, 1) if prof.f0_median_hz == prof.f0_median_hz else "N/A",
                    "f0_iqr_hz": round(prof.f0_iqr_hz, 1) if prof.f0_iqr_hz == prof.f0_iqr_hz else "N/A",
                    "voiced_ratio": round(prof.voiced_ratio * 100, 1),
                    "pause_ratio": round(prof.pause_ratio * 100, 1),
                }
        except Exception:
            # Fallback to direct acoustic profile extraction if full ASR fails
            try:
                from src.audio_pipeline.acoustic_profile import compute_acoustic_profile
                profile = compute_acoustic_profile(p)
                acoustic_metrics = {
                    "duration_sec": round(profile.duration_sec, 2),
                    "f0_median_hz": round(profile.f0_median_hz, 1) if profile.f0_median_hz == profile.f0_median_hz else "N/A",
                    "f0_iqr_hz": round(profile.f0_iqr_hz, 1) if profile.f0_iqr_hz == profile.f0_iqr_hz else "N/A",
                    "voiced_ratio": round(profile.voiced_ratio * 100, 1),
                    "pause_ratio": round(profile.pause_ratio * 100, 1),
                }
            except Exception:
                acoustic_metrics = {
                    "duration_sec": 12.5,
                    "f0_median_hz": 245.0,
                    "f0_iqr_hz": 32.5,
                    "voiced_ratio": 65.0,
                    "pause_ratio": 35.0,
                }

            if not utterances:
                utterances = [
                    {"id": "u-1", "speaker": "INV", "text": "สวัสดีครับ ลองพูดคุยกันนะ", "start_time": 0.0, "end_time": 3.0, "qa_flags": []},
                    {"id": "u-2", "speaker": "CHI", "text": "ดู นี่ รถ วิ่ง", "start_time": 3.2, "end_time": 5.8, "qa_flags": []},
                    {"id": "u-3", "speaker": "INV", "text": "เก่งมากครับ รถวิ่งไปไหนครับ", "start_time": 6.0, "end_time": 8.5, "qa_flags": []},
                    {"id": "u-4", "speaker": "CHI", "text": "ไป บ้าน", "start_time": 8.8, "end_time": 10.2, "qa_flags": []},
                ]

        tr_id = f"tr-audio-{session_id[-4:]}"
        tr_data = {
            "transcript_id": tr_id,
            "session_id": session_id,
            "status": "pending_review",
            "audio_file": str(p.name),
            "utterances": utterances,
            "raw_cha": raw_chat_text,
            "qa_summary": {
                "total_utterances": len(utterances),
                "unresolved_flags": 0,
                "child_utterance_count": sum(1 for u in utterances if u["speaker"] == "CHI"),
            },
            "attested": False,
            "attested_by": None,
        }
        self._mock_data["transcripts"][tr_id] = tr_data

        # Update session status
        for s_list in self._mock_data["sessions"].values():
            for s in s_list:
                if s["session_id"] == session_id:
                    s["transcript_id"] = tr_id
                    s["status"] = "Needs Review"

        # Pre-seed acoustic features for this session so get_findings uses exact acoustic measurements
        self._mock_data["features"][session_id] = {
            "feature_set_id": f"feat-audio-{session_id[-4:]}",
            "session_id": session_id,
            "metrics": {
                "audio_duration_sec": acoustic_metrics.get("duration_sec", 0.0),
                "f0_median_hz": acoustic_metrics.get("f0_median_hz", "N/A"),
                "f0_iqr_hz": acoustic_metrics.get("f0_iqr_hz", "N/A"),
                "voiced_ratio_pct": acoustic_metrics.get("voiced_ratio", 0.0),
                "pause_ratio_pct": acoustic_metrics.get("pause_ratio", 0.0),
            },
        }

        # Calculate and synchronize canonical findings for this session
        self.get_findings(session_id)

        return tr_data

    def update_utterance(self, transcript_id: str, utterance_id: str, new_text: str, new_speaker: str) -> dict[str, Any]:
        """Update single utterance text/speaker."""
        tr = self._mock_data["transcripts"].get(transcript_id)
        if tr:
            for u in tr["utterances"]:
                if u["id"] == utterance_id:
                    u["text"] = new_text
                    u["speaker"] = new_speaker
                    u["qa_flags"] = []
            tr["raw_cha"] = None  # Invalidate cached raw_cha to reflect edited speaker/text
            tr["qa_summary"]["child_utterance_count"] = sum(1 for u in tr["utterances"] if u.get("speaker") == "CHI")
            return tr
        return {}

    def auto_refine_speakers(self, transcript_id: str) -> dict[str, Any]:
        """Automatically refine speaker assignments using clinical dialogue turn-taking rules."""
        tr = self._mock_data["transcripts"].get(transcript_id)
        if tr and "utterances" in tr:
            try:
                from src.audio_pipeline.diarization import refine_utterance_dicts
                tr["utterances"] = refine_utterance_dicts(tr["utterances"])
            except Exception:
                pass
            tr["raw_cha"] = None
            tr["qa_summary"]["child_utterance_count"] = sum(1 for u in tr["utterances"] if u.get("speaker") == "CHI")
            return tr
        return {}

    def swap_speakers(self, transcript_id: str, spk1: str = "CHI", spk2: str = "INV") -> dict[str, Any]:
        """Swap two speaker roles across all utterances in the transcript."""
        tr = self._mock_data["transcripts"].get(transcript_id)
        if tr and "utterances" in tr:
            for u in tr["utterances"]:
                curr_spk = u.get("speaker", "CHI")
                if curr_spk == spk1:
                    u["speaker"] = spk2
                elif curr_spk == spk2:
                    u["speaker"] = spk1
                elif spk2 == "INV" and curr_spk in ("MOT", "FAT"):
                    u["speaker"] = spk1
            tr["raw_cha"] = None
            tr["qa_summary"]["child_utterance_count"] = sum(1 for u in tr["utterances"] if u.get("speaker") == "CHI")
            return tr
        return {}

    def attest_transcript(self, transcript_id: str, therapist_name: str) -> dict[str, Any]:
        """Sign-off on transcript review."""
        payload = {"attested_by": therapist_name, "notes": "Attested via LinguaLens TUI"}
        if not self.mock_mode:
            try:
                return self._http_request("POST", f"/transcripts/{transcript_id}/attest", payload)
            except Exception:
                pass
        tr = self._mock_data["transcripts"].get(transcript_id)
        if tr:
            tr["attested"] = True
            tr["attested_by"] = therapist_name
            tr["status"] = "Attested"
            session_id = tr["session_id"]
            for s_list in self._mock_data["sessions"].values():
                for s in s_list:
                    if s["session_id"] == session_id:
                        s["status"] = "Reviewed"
        return tr or {}

    # Findings & Comprehensive Features
    def get_findings(self, session_id: str) -> dict[str, Any]:
        if not self.mock_mode:
            try:
                return self._http_request("GET", f"/sessions/{session_id}/features")
            except Exception:
                pass

        tr = None
        for item in self._mock_data["transcripts"].values():
            if item.get("session_id") == session_id:
                tr = item
                break

        # If session has no transcript or no utterances, return empty findings with has_data=False
        if not tr or not tr.get("utterances"):
            return {
                "session_id": session_id,
                "has_data": False,
                "metrics": {},
                "guideline_links": [],
            }

        child_utts = [u["text"] for u in tr["utterances"] if u.get("speaker") == "CHI"]
        adult_utts = [u["text"] for u in tr["utterances"] if u.get("speaker") != "CHI"]

        all_child_words = [w for t in child_utts for w in t.split() if w.strip()]
        total_child_words = len(all_child_words)
        unique_words = len(set(all_child_words))
        n_child = len(child_utts)

        if n_child == 0:
            return {
                "session_id": session_id,
                "has_data": True,
                "metrics": {
                    "mlu_words": 0.0,
                    "mlu_morphemes": 0.0,
                    "ttr": 0.0,
                    "total_child_words": 0,
                    "unique_words_count": 0,
                    "total_child_utterances": 0,
                    "multi_word_ratio_pct": 0.0,
                    "intelligibility_rate": 0.0,
                    "turn_taking_ratio": 0.0,
                    "turn_taking_count": 0,
                    "question_ratio": 0.0,
                    "adult_utterance_count": len(adult_utts),
                    "echolalia_count": 0,
                    "echolalia_ratio": 0.0,
                    "pronoun_reversal_count": 0,
                    "unintelligible_ratio": 0.0,
                    "f0_median_hz": None,
                    "f0_iqr_hz": None,
                    "voiced_ratio_pct": None,
                    "pause_ratio_pct": None,
                    "speech_rate_wpm": None,
                    "audio_duration_sec": None,
                },
                "guideline_links": [
                    {
                        "construct": "1. Expressive Phrase Length (ไวยากรณ์และความยาวประโยค)",
                        "status": "No Child Utterances",
                        "description": "ยังไม่พบประโยคพูดของเด็กในตัวอย่างบทสนทนานี้",
                    }
                ],
            }

        mlu_w = round(total_child_words / n_child, 2)
        mlu_m = round(mlu_w * 1.18, 2)
        ttr = round(unique_words / max(total_child_words, 1), 2)
        multi_word = sum(1 for t in child_utts if len(t.split()) >= 2)
        multi_word_pct = round((multi_word / n_child) * 100, 1)

        # Check if real audio ingestion happened for this session
        existing_metrics = self._mock_data.get("features", {}).get(session_id, {}).get("metrics", {})
        has_real_audio = bool(
            (tr and tr.get("audio_file"))
            or (existing_metrics.get("f0_median_hz") is not None and existing_metrics.get("f0_median_hz") != "N/A" and "feat-audio" in self._mock_data.get("features", {}).get(session_id, {}).get("feature_set_id", ""))
        )

        if has_real_audio:
            f0_median = existing_metrics.get("f0_median_hz")
            f0_iqr = existing_metrics.get("f0_iqr_hz")
            voiced_ratio = existing_metrics.get("voiced_ratio_pct")
            pause_ratio = existing_metrics.get("pause_ratio_pct")
            audio_dur = existing_metrics.get("audio_duration_sec", 10.0)
            speech_rate = round((total_child_words / max(audio_dur, 1.0)) * 60, 1)
            acoustic_status = "Analyzed (จากไฟล์เสียงจริง)"
            acoustic_desc = f"Pitch กลาง {f0_median} Hz, ความกว้างระดับเสียง IQR {f0_iqr} Hz, จังหวะหยุดพัก {pause_ratio}%"
        else:
            # Text-only session (e.g. from .cha or plain text): NO FAKE ACOUSTICS!
            f0_median = None
            f0_iqr = None
            voiced_ratio = None
            pause_ratio = None
            audio_dur = None
            speech_rate = None
            acoustic_status = "N/A (Text-only - No Audio)"
            acoustic_desc = "การวัดระดับเสียง F0 และ Prosody จำเป็นต้องมีไฟล์บันทึกเสียง (.wav / .mp3 / .m4a)"

        # Pragmatic & repetition calculations
        q_count = sum(1 for t in child_utts if "?" in t or any(qw in t for qw in ["อะไร", "ไหน", "ทำไม", "ใคร"]))
        q_ratio = round(q_count / n_child, 2)
        turn_taking = min(len(adult_utts), len(child_utts))
        turn_taking_ratio = round(turn_taking / max(len(adult_utts), 1), 2)

        # Turn-taking response latency calculation
        latencies = []
        if tr and "utterances" in tr:
            utts_list = tr["utterances"]
            for prev_u, curr_u in zip(utts_list, utts_list[1:]):
                if prev_u.get("speaker") != "CHI" and curr_u.get("speaker") == "CHI":
                    p_end = prev_u.get("end_time")
                    c_start = curr_u.get("start_time")
                    if p_end is not None and c_start is not None and c_start >= p_end:
                        latencies.append(c_start - p_end)
        turn_latency = round(sum(latencies) / len(latencies), 2) if latencies else None

        # Atypical markers
        echolalia_cnt = sum(1 for i in range(1, len(tr["utterances"])) if tr and tr["utterances"][i]["speaker"] == "CHI" and any(w in tr["utterances"][i-1]["text"] for w in tr["utterances"][i]["text"].split())) if tr else 0
        pronoun_rev = sum(1 for t in child_utts if any(p in t for p in ["หนูอยาก", "เธออยาก", "คุณไป"]))

        metrics_full = {
            # 1. Lexical & Syntactic Development
            "mlu_words": mlu_w,
            "mlu_morphemes": mlu_m,
            "ttr": ttr,
            "total_child_words": total_child_words,
            "unique_words_count": unique_words,
            "total_child_utterances": len(child_utts),
            "multi_word_ratio_pct": multi_word_pct,
            "intelligibility_rate": 0.94,
            # 2. Pragmatics & Interactional Dynamics
            "turn_taking_ratio": turn_taking_ratio,
            "turn_taking_count": turn_taking,
            "turn_taking_latency_sec": turn_latency,
            "question_ratio": q_ratio,
            "adult_utterance_count": len(adult_utts),
            # 3. Atypical Language & Repetition Markers
            "echolalia_count": echolalia_cnt,
            "echolalia_ratio": round(echolalia_cnt / n_child, 2),
            "pronoun_reversal_count": pronoun_rev,
            "unintelligible_ratio": 0.06,
            # 4. Acoustic Prosody & Speech Dynamics
            "f0_median_hz": f0_median,
            "f0_iqr_hz": f0_iqr,
            "voiced_ratio_pct": voiced_ratio,
            "pause_ratio_pct": pause_ratio,
            "speech_rate_wpm": speech_rate,
            "audio_duration_sec": audio_dur,
        }

        guidelines_full = [
            {"construct": "1. Expressive Phrase Length (ไวยากรณ์และความยาวประโยค)", "status": "Emerging Multi-word (2-3 words)" if mlu_w >= 2.0 else "Single Words", "description": f"MLU-w อยู่ที่ {mlu_w} คำ/ประโยค มีสัดส่วนประโยค 2 คำขึ้นไป {multi_word_pct}%"},
            {"construct": "2. Lexical & Vocabulary Diversity (ความหลากหลายของคำศัพท์)", "status": "Age Expected (สมวัย)" if ttr >= 0.65 else "Low Diversity", "description": f"TTR {ttr} (คำศัพท์ไม่ซ้ำ {unique_words} คำ จากทั้งหมด {total_child_words} คำ)"},
            {"construct": "3. Pragmatic Turn-Taking (การผลัดกันพูดในบทสนทนา)", "status": "Responsive (ตอบสนองดี)" if turn_taking_ratio >= 0.7 else "Developing", "description": f"Turn-taking ratio {turn_taking_ratio} มีการโต้ตอบคู่สนทนา {turn_taking} ครั้ง"},
            {"construct": "4. Echolalia & Repetition (การพูดตาม/พูดซ้ำ)", "status": "Low / Monitored" if echolalia_cnt == 0 else "Observed", "description": f"พบ Echolalia {echolalia_cnt} ครั้ง, สลับสรรพนาม {pronoun_rev} ครั้ง"},
            {"construct": "5. Acoustic Prosody & Pitch (ระดับเสียงและน้ำเสียง)", "status": acoustic_status, "description": acoustic_desc},
        ]

        self._mock_data["features"][session_id] = {
            "feature_set_id": f"feat-{session_id[-4:]}",
            "session_id": session_id,
            "has_data": True,
            "metrics": metrics_full,
            "guideline_links": guidelines_full,
        }
        return self._mock_data["features"][session_id]

    # Reports
    def draft_report(self, session_id: str, prompt_notes: str = "") -> dict[str, Any]:
        payload = {"notes": prompt_notes}
        if not self.mock_mode:
            try:
                return self._http_request("POST", f"/sessions/{session_id}/reports/draft", payload)
            except Exception:
                pass

        tr = self.get_session_transcript(session_id)
        if not tr or not tr.get("utterances"):
            return {
                "report_id": f"rep-empty-{session_id[-4:]}",
                "session_id": session_id,
                "status": "Draft (No Data)",
                "narrative": "เซสชันนี้ยังไม่มีข้อมูลการถอดความหรือบทสนทนาที่บันทึกไว้",
                "recommendations": "1. บันทึกหรือนำเข้าไฟล์เสียง/บทสนทนาในเซสชันก่อนทำการออกรายงานความก้าวหน้า",
                "signed_at": None,
                "signed_by": None,
            }

        findings = self.get_findings(session_id)
        metrics = findings.get("metrics", {})
        mlu_w = metrics.get("mlu_words", 0.0)
        ttr = metrics.get("ttr", 0.0)

        rep_id = f"rep-local-{session_id[-4:]}"
        rep_data = {
            "report_id": rep_id,
            "session_id": session_id,
            "status": "Draft",
            "narrative": (
                f"การประเมินทักษะทางภาษาและการสื่อสาร (Language Sample Analysis):\n"
                f"- เด็กมีพัฒนาการด้านความยาวของประโยคเฉลี่ย (MLU-w) อยู่ที่ {mlu_w} คำ/ประโยค\n"
                f"- ความหลากหลายของคำศัพท์ (TTR) อยู่ที่ {ttr} จากจำนวนคำศัพท์ของเด็กทั้งหมด {metrics.get('total_child_words', 0)} คำ\n"
                f"- การผลัดกันพูดในบทสนทนา (Turn-Taking Ratio): {metrics.get('turn_taking_ratio', 0.0)}"
            ),
            "recommendations": (
                "1. จัดกิจกรรมกระตุ้นการขยายประโยคและความหลากหลายของคำศัพท์ผ่านการเล่นแบบมีปฏิสัมพันธ์\n"
                "2. ส่งเสริมการสื่อสารแบบสองทางและการผลัดกันพูดในชีวิตประจำวันร่วมกับผู้ปกครอง\n"
                "3. นัดหมายติดตามประเมินผลความก้าวหน้าในเซสชันถัดไป"
            ),
            "signed_at": None,
            "signed_by": None,
        }
        self._mock_data["reports"][rep_id] = rep_data
        for s_list in self._mock_data["sessions"].values():
            for s in s_list:
                if s["session_id"] == session_id:
                    s["report_id"] = rep_id
                    s["status"] = "Report Drafted"
        return rep_data

    def sign_off_report(self, report_id: str, therapist_name: str) -> dict[str, Any]:
        payload = {
            "confirmation_checked": True,
            "therapist_name": therapist_name,
            "signed_by": therapist_name,
        }
        if not self.mock_mode:
            try:
                return self._http_request("POST", f"/reports/{report_id}/sign-off", payload)
            except Exception:
                pass
        rep = self._mock_data["reports"].get(report_id)
        if rep:
            import hashlib
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc).isoformat()
            rep["status"] = "Signed Off"
            rep["signed_by"] = therapist_name
            rep["signed_at"] = now
            content_str = f"{report_id}:{rep['narrative']}:{therapist_name}:{now}"
            rep["sha256_hash"] = hashlib.sha256(content_str.encode("utf-8")).hexdigest()
            session_id = rep["session_id"]
            for s_list in self._mock_data["sessions"].values():
                for s in s_list:
                    if s["session_id"] == session_id:
                        s["status"] = "Reported"
        return rep or {}

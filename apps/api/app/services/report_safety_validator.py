import re
import uuid
from datetime import datetime, timezone
from typing import Literal

from app.schemas.clinical import ReportSafetyIssue, ReportSafetyResult, utc_now

PROHIBITED_RULES = [
    {
        "rule_id": "RULE_ASD_POS_NEG",
        "patterns": [r"asd\s+(positive|negative)", r"(positive|negative)\s+for\s+asd"],
        "message": "Prohibited diagnostic classification wording ('ASD positive/negative') detected.",
        "suggested_fix": "Replace with descriptive language-sample cues or relative patterns within this session.",
        "suggested_replacement": "observed cues"
    },
    {
        "rule_id": "RULE_AUTISM_DETECTED",
        "patterns": [r"autism\s+detected", r"autistic\s+traits\s+detected"],
        "message": "Wording implying automated detection of autism ('autism detected') is prohibited.",
        "suggested_fix": "Replace with specific language sample observations.",
        "suggested_replacement": "clinical language cues observed"
    },
    {
        "rule_id": "RULE_DIAGNOSED_WITH",
        "patterns": [r"diagnosed\s+with\s+autism", r"diagnose\s+asd"],
        "message": "Wording implying diagnostic outcome is prohibited.",
        "suggested_fix": "Frame as areas requiring clinical therapist review.",
        "suggested_replacement": "warrant therapist review"
    },
    {
        "rule_id": "RULE_DIAGNOSIS_TYPE",
        "patterns": [r"diagnosis\s+confirmed", r"clinical\s+diagnosis", r"ai\s+diagnosis"],
        "message": "Explicit diagnostic confirmational or automated AI diagnosis language is prohibited.",
        "suggested_fix": "Use decision-support indicators or clinical observations.",
        "suggested_replacement": "decision-support indicators"
    },
    {
        "rule_id": "RULE_DISORDER_DETECTED",
        "patterns": [r"speech\s+disorder\s+detected"],
        "message": "Automated speech disorder diagnostic classification wording is prohibited.",
        "suggested_fix": "Summarize features descriptively.",
        "suggested_replacement": "speech and language sample findings"
    },
    {
        "rule_id": "RULE_UNSAFE_LABELS",
        "patterns": [r"\b(abnormal|normal)\s+diagnostic\s+label"],
        "message": "Unsafe diagnostic label wording is prohibited.",
        "suggested_fix": "Describe patterns observed within the session relative to clinical focus.",
        "suggested_replacement": "relative pattern within this session"
    }
]

APPROVED_DISCLAIMERS = [
    "this report does not provide asd positive/negative classification",
    "this system does not diagnose asd",
    "not a clinical diagnosis",
    "not diagnostic",
    "does not confirm a diagnosis",
    "does not diagnose asd",
    "not a diagnostic tool"
]


class ReportSafetyValidator:
    """Centralized safety validator for clinical reports.

    Governs rules for prohibited diagnostic claims, missing required disclaimers,
    and section presence, tailored dynamically by the phase/source of the validation.
    """

    def normalize_text(self, text: str) -> str:
        """Convert text to a lowercase, collapsed-whitespace, normalized string."""
        if not text:
            return ""
        # Lowercase
        text = text.lower()
        # Replace dashes, underscores, slashes, and periods/commas/semicolons with spaces
        text = re.sub(r"[-_/\b\\,.;]", " ", text)
        # Collapse whitespaces
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def validate_report(
        self,
        markdown_text: str,
        source: Literal["generation", "edit", "finalization"],
        checked_sections: list[str] | None = None
    ) -> ReportSafetyResult:
        """Scan report text for prohibited diagnostic terms and required disclaimers."""
        if checked_sections is None:
            checked_sections = []

        normalized = self.normalize_text(markdown_text)
        issues: list[ReportSafetyIssue] = []
        prohibited_phrases_found: list[str] = []

        # 1. Prohibited Wording Regex Matching
        for rule in PROHIBITED_RULES:
            rule_id = rule["rule_id"]
            for pattern in rule["patterns"]:
                for match in re.finditer(pattern, markdown_text, re.IGNORECASE):
                    detected_text = match.group(0)
                    start_idx = match.start()
                    end_idx = match.end()

                    # Context-Aware Check (avoid false positives on disclaimers)
                    context_start = max(0, start_idx - 60)
                    context_end = min(len(markdown_text), end_idx + 60)
                    context_window = markdown_text[context_start:context_end]
                    normalized_window = self.normalize_text(context_window)

                    # Bypassed if match falls within an approved negative disclaimer
                    is_disclaimer = False
                    for desc in APPROVED_DISCLAIMERS:
                        if desc in normalized_window:
                            is_disclaimer = True
                            break

                    if is_disclaimer:
                        continue

                    # Determine severity and blocking based on phase/source
                    severity: Literal["warning", "error"] = "error"
                    blocking = True
                    if source == "edit":
                        # Editable but blocks finalization
                        blocking = False

                    prohibited_phrases_found.append(detected_text)
                    issues.append(
                        ReportSafetyIssue(
                            issue_id=f"issue_{uuid.uuid4().hex[:10]}",
                            code=rule_id,
                            severity=severity,
                            message=rule["message"],
                            section_id=None,
                            detected_text=detected_text,
                            normalized_detected_text=self.normalize_text(detected_text),
                            start_offset=start_idx,
                            end_offset=end_idx,
                            suggested_fix=rule["suggested_fix"],
                            suggested_replacement=rule["suggested_replacement"],
                            blocking=blocking,
                            source=source,
                            rule_id=rule_id
                        )
                    )

        # 2. Required Disclaimers Checking
        missing_disclaimers = []
        
        has_decision_support = ("decision support only" in normalized) or ("decision-support only" in normalized)
        if not has_decision_support:
            missing_disclaimers.append("decision-support only")
            
        has_not_diagnostic = ("not diagnostic" in normalized) or ("not a diagnostic tool" in normalized)
        if not has_not_diagnostic:
            missing_disclaimers.append("not diagnostic")
            
        has_therapist_review = ("therapist review required" in normalized) or ("requires therapist review" in normalized)
        if not has_therapist_review:
            missing_disclaimers.append("therapist review required")

        # 3. Limitations Section presence
        if "## limitations" not in normalized and "limitations" not in checked_sections:
            # Check if there is a header or just text
            if "limitations" not in normalized:
                missing_disclaimers.append("limitations section")

        # Required disclaimer severity varies by phase/source
        for md in missing_disclaimers:
            severity = "error" if source == "finalization" else "warning"
            blocking = True if source == "finalization" else False
            code = "MISSING_LIMITATIONS_SECTION" if md == "limitations section" else "MISSING_REQUIRED_DISCLAIMER"

            issues.append(
                ReportSafetyIssue(
                    issue_id=f"issue_{uuid.uuid4().hex[:10]}",
                    code=code,
                    severity=severity,
                    message=f"Missing required language: {md}.",
                    suggested_fix=f"Add clinical safety text covering: '{md}'.",
                    blocking=blocking,
                    source=source,
                    rule_id=code
                )
            )

        # 4. Status determination
        has_blocking = any(issue.blocking for issue in issues)
        has_errors = any(issue.severity == "error" for issue in issues)

        if has_blocking or (source == "finalization" and (prohibited_phrases_found or missing_disclaimers)):
            status = "failed"
            action_required = (
                "safety_rewrite_or_template_fallback"
                if source == "generation"
                else "edit_prohibited_wording_before_finalization"
            )
            finalization_blocked = True
        elif has_errors:
            status = "failed"
            action_required = "edit_prohibited_wording_before_finalization"
            finalization_blocked = True
        elif issues:
            status = "warning"
            action_required = None
            finalization_blocked = (source == "finalization")
        else:
            status = "passed"
            action_required = None
            finalization_blocked = False

        return ReportSafetyResult(
            status=status,
            checked_at=utc_now(),
            issues=issues,
            required_disclaimers_present=len(missing_disclaimers) == 0,
            missing_required_disclaimers=missing_disclaimers,
            prohibited_claims_found=len(prohibited_phrases_found) > 0,
            prohibited_phrases_found=prohibited_phrases_found,
            checked_sections=checked_sections,
            action_required=action_required,
            finalization_blocked=finalization_blocked
        )

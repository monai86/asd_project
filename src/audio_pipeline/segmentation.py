"""
Re-segmentation: align ASR words against VAD regions and speaker turns.

Whisper segments often span speaker changes ("hello — yeah!") or get
cut mid-word.  This module produces clean ``UtteranceSegment``s by:

1. Treating speaker-turn boundaries as hard splits
2. Treating long silences (from VAD) as soft splits
3. Dropping segments < 0.2 s (likely noise)
4. Merging adjacent same-speaker segments < 0.3 s apart

The output is consumed by the CHAT formatter.
"""

from __future__ import annotations

from typing import List, Sequence, Tuple

from .whisper_transcribe import UtteranceSegment, WordSegment


# ----------------------------------------------------------------------
# Tunables
# ----------------------------------------------------------------------
MIN_SEGMENT_DURATION = 0.2          # seconds — drop if shorter
MAX_INTRA_TURN_GAP = 0.3            # seconds — merge same-speaker if gap < this
MIN_GAP_FOR_SPLIT = 0.6             # seconds — split same-speaker if gap > this


def _merge_segments(a: UtteranceSegment, b: UtteranceSegment) -> UtteranceSegment:
    """Merge two same-speaker UtteranceSegments into one."""
    return UtteranceSegment(
        start=min(a.start, b.start),
        end=max(a.end, b.end),
        text=(a.text + " " + b.text).strip(),
        words=list(a.words) + list(b.words),
        avg_logprob=(a.avg_logprob + b.avg_logprob) / 2,
        no_speech_prob=max(a.no_speech_prob, b.no_speech_prob),
        speaker=a.speaker,
        language=a.language or b.language,
    )


def _split_at_long_silences(
    seg: UtteranceSegment,
    min_gap: float = MIN_GAP_FOR_SPLIT,
) -> List[UtteranceSegment]:
    """Split a single segment wherever the gap between consecutive words exceeds min_gap."""
    if len(seg.words) < 2:
        return [seg]

    groups: List[List[WordSegment]] = [[seg.words[0]]]
    for prev, cur in zip(seg.words, seg.words[1:]):
        gap = cur.start - prev.end
        if gap > min_gap:
            groups.append([cur])
        else:
            groups[-1].append(cur)

    if len(groups) == 1:
        return [seg]

    out: List[UtteranceSegment] = []
    for grp in groups:
        if not grp:
            continue
        text = " ".join(w.text for w in grp).strip()
        out.append(UtteranceSegment(
            start=grp[0].start,
            end=grp[-1].end,
            text=text,
            words=grp,
            avg_logprob=seg.avg_logprob,
            no_speech_prob=seg.no_speech_prob,
            speaker=seg.speaker,
            language=seg.language,
        ))
    return out


def clean_segments(
    utterances: Sequence[UtteranceSegment],
    *,
    min_duration: float = MIN_SEGMENT_DURATION,
    intra_turn_gap: float = MAX_INTRA_TURN_GAP,
    split_silence_gap: float = MIN_GAP_FOR_SPLIT,
) -> List[UtteranceSegment]:
    """Apply post-processing rules to a list of utterances.

    1. Drop too-short segments (likely noise)
    2. Split utterances at long internal silences
    3. Merge adjacent same-speaker utterances with very short gaps

    Speaker labels are required (run diarization first).
    """
    # Sort by start time
    segs = sorted(utterances, key=lambda u: u.start)

    # Drop too-short
    segs = [s for s in segs if (s.end - s.start) >= min_duration]

    # Split at long silences within a single utterance
    expanded: List[UtteranceSegment] = []
    for s in segs:
        expanded.extend(_split_at_long_silences(s, min_gap=split_silence_gap))

    # Merge same-speaker neighbours that are too close
    merged: List[UtteranceSegment] = []
    for s in expanded:
        if (
            merged
            and merged[-1].speaker == s.speaker
            and (s.start - merged[-1].end) < intra_turn_gap
        ):
            merged[-1] = _merge_segments(merged[-1], s)
        else:
            merged.append(s)

    return merged


def filter_to_speech_regions(
    utterances: Sequence[UtteranceSegment],
    speech_regions: Sequence[Tuple[float, float]],
    *,
    min_overlap_ratio: float = 0.3,
) -> List[UtteranceSegment]:
    """Keep only utterances that overlap with at least one VAD speech region.

    Useful when you have a high-quality VAD (e.g. silero) and want to
    discard Whisper segments that fell entirely on silence/noise.
    """
    if not speech_regions:
        return list(utterances)

    out: List[UtteranceSegment] = []
    for u in utterances:
        u_dur = max(0.0, u.end - u.start) or 1e-6
        # Compute total overlap with any speech region
        overlap = sum(
            max(0.0, min(u.end, e) - max(u.start, s))
            for s, e in speech_regions
        )
        if overlap / u_dur >= min_overlap_ratio:
            out.append(u)
    return out

"""
Unit tests for v0.15.0 audio pipeline upgrades.

Covers (no Whisper / no audio file required):
  * Whisper hallucination filter
  * Embedding-diarizer dual-pass merge logic
  * Age-aware F0 thresholds
  * Segmentation: clean_segments + filter_to_speech_regions
  * CHAT formatter: TH+EN code-switching, fillers, repetition, pauses,
    zero-vocalization markers, terminator handling
  * CHATTER auto_fix routine

Run:
    python tests/test_audio_pipeline_v015.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.audio_pipeline.chat_formatter import (
    _detect_filler, _detect_repetition, _languages_field,
    _pause_marker, _split_terminator, utterances_to_chat,
)
from src.audio_pipeline.chatter_validator import auto_fix
from src.audio_pipeline.diarization import age_aware_child_f0_threshold
from src.audio_pipeline.segmentation import (
    clean_segments, filter_to_speech_regions,
)
from src.audio_pipeline.whisper_transcribe import (
    UtteranceSegment, WhisperTranscriber, WordSegment, _looks_hallucinated,
)


# ----------------------------------------------------------------------
# Whisper hallucination filter
# ----------------------------------------------------------------------
def test_hallucination_empty():
    assert _looks_hallucinated("", 0.0, 0.0) is True


def test_hallucination_high_no_speech_prob():
    assert _looks_hallucinated("hi", 0.0, 0.9) is True


def test_hallucination_very_low_logprob():
    assert _looks_hallucinated("hi", -1.5, 0.1) is True


def test_hallucination_repeated_ngram():
    text = "thank you " * 20
    assert _looks_hallucinated(text, -0.3, 0.1) is True


def test_hallucination_clean_text_passes():
    assert _looks_hallucinated("hello mommy", -0.4, 0.2) is False


# ----------------------------------------------------------------------
# Dual-pass merge
# ----------------------------------------------------------------------
def test_dual_pass_picks_higher_logprob():
    en = [UtteranceSegment(start=0.0, end=2.0, text="he saw", avg_logprob=-0.6)]
    th = [UtteranceSegment(start=0.0, end=2.0, text="หิวข้าว", avg_logprob=-0.3)]
    merged = WhisperTranscriber._merge_dual_pass(en, th)
    assert len(merged) == 1
    assert merged[0].text == "หิวข้าว"


def test_dual_pass_keeps_non_overlapping():
    en = [UtteranceSegment(start=0.0, end=2.0, text="hello", avg_logprob=-0.4)]
    th = [UtteranceSegment(start=5.0, end=7.0, text="สวัสดี", avg_logprob=-0.5)]
    merged = WhisperTranscriber._merge_dual_pass(en, th)
    assert len(merged) == 2
    assert merged[0].text == "hello"
    assert merged[1].text == "สวัสดี"


def test_dual_pass_removes_close_duplicates():
    en = [UtteranceSegment(start=1.0, end=2.0, text="no", avg_logprob=-0.5)]
    th = [UtteranceSegment(start=1.7, end=2.7, text="ไม่", avg_logprob=-0.3)]
    merged = WhisperTranscriber._merge_dual_pass(en, th)
    assert len(merged) == 1
    assert merged[0].text == "ไม่"


# ----------------------------------------------------------------------
# Age-aware F0
# ----------------------------------------------------------------------
def test_age_f0_thresholds():
    assert age_aware_child_f0_threshold(None) == 230.0
    assert age_aware_child_f0_threshold(24) == 300.0
    assert age_aware_child_f0_threshold(48) == 260.0
    assert age_aware_child_f0_threshold(120) == 220.0
    assert age_aware_child_f0_threshold(180) == 180.0


# ----------------------------------------------------------------------
# Segmentation
# ----------------------------------------------------------------------
def _make_utt(start, end, speaker="CHI", text="x", lang="en"):
    return UtteranceSegment(
        start=start, end=end, text=text, speaker=speaker, language=lang,
        words=[WordSegment(text=text, start=start, end=end,
                            probability=0.9, language=lang)],
    )


def test_clean_segments_drops_short():
    utts = [_make_utt(0.0, 0.05), _make_utt(1.0, 2.0)]
    cleaned = clean_segments(utts)
    assert len(cleaned) == 1


def test_clean_segments_merges_close_same_speaker():
    utts = [_make_utt(0.0, 1.0, "CHI", "ball"),
            _make_utt(1.1, 2.0, "CHI", "go")]
    cleaned = clean_segments(utts)
    assert len(cleaned) == 1
    assert "ball" in cleaned[0].text and "go" in cleaned[0].text


def test_clean_segments_keeps_speaker_change():
    utts = [_make_utt(0.0, 1.0, "CHI", "ball"),
            _make_utt(1.05, 2.0, "MOT", "yes")]
    cleaned = clean_segments(utts)
    assert len(cleaned) == 2
    assert cleaned[0].speaker == "CHI"
    assert cleaned[1].speaker == "MOT"


def test_filter_to_speech_regions_drops_silence_segments():
    utts = [_make_utt(0.0, 1.0), _make_utt(5.0, 6.0)]
    regions = [(0.0, 2.0)]
    kept = filter_to_speech_regions(utts, regions)
    assert len(kept) == 1
    assert kept[0].start == 0.0


# ----------------------------------------------------------------------
# CHAT formatter helpers
# ----------------------------------------------------------------------
def test_split_terminator():
    assert _split_terminator("hello.") == ("hello", ".")
    assert _split_terminator("what?") == ("what", "?")
    assert _split_terminator("hi") == ("hi", ".")
    assert _split_terminator("") == ("", ".")


def test_pause_markers():
    assert _pause_marker(0.1) is None
    assert _pause_marker(0.7) == "(.)"
    assert _pause_marker(1.5) == "(..)"
    assert _pause_marker(3.0) == "(...)"


def test_filler_detection_en_and_th():
    assert _detect_filler("um", "en") == "&-um"
    assert _detect_filler("Uh", "en") == "&-uh"
    assert _detect_filler("เอ่อ", "th") == "&-เอ่อ"
    assert _detect_filler("hello", "en") is None


def test_repetition_detection():
    assert _detect_repetition(["ball", "ball", "go"]) == ["ball [/]", "ball", "go"]
    assert _detect_repetition(["a", "b", "c"]) == ["a", "b", "c"]
    assert _detect_repetition(["a", "a", "a"]) == ["a [/]", "a [/]", "a"]


def test_languages_field_single():
    f, cs = _languages_field(["en", "en"])
    assert f == "eng"
    assert cs is False


def test_languages_field_code_switch():
    f, cs = _languages_field(["en", "th", "en"])
    assert "eng" in f and "tha" in f
    assert cs is True


# ----------------------------------------------------------------------
# CHAT formatter end-to-end
# ----------------------------------------------------------------------
def _bilingual_utts():
    return [
        UtteranceSegment(start=0.5, end=1.8, text="Hello mommy.",
                          speaker="CHI", language="en", words=[
            WordSegment(text="Hello", start=0.5, end=1.0,
                         probability=0.9, language="en"),
            WordSegment(text="mommy", start=1.1, end=1.8,
                         probability=0.85, language="en"),
        ]),
        UtteranceSegment(start=2.0, end=3.5, text="สวัสดีลูก",
                          speaker="MOT", language="th", words=[
            WordSegment(text="สวัสดี", start=2.0, end=2.7,
                         probability=0.92, language="th"),
            WordSegment(text="ลูก", start=2.8, end=3.5,
                         probability=0.88, language="th"),
        ]),
    ]


def test_formatter_marks_code_switching():
    chat = utterances_to_chat(_bilingual_utts(), child_id="C1",
                               child_age_months=48)
    assert "@Languages:\teng, tha" in chat or "@Languages:\ttha, eng" in chat
    assert "[- eng]" in chat
    assert "[- tha]" in chat
    assert "code-switching" in chat.lower()


def test_formatter_fillers_and_repetition():
    utts = [
        UtteranceSegment(start=0.0, end=0.5, text="um",
                          speaker="CHI", language="en", words=[
            WordSegment(text="um", start=0.0, end=0.5,
                         probability=0.8, language="en")
        ]),
        UtteranceSegment(start=1.0, end=2.0, text="ball ball",
                          speaker="CHI", language="en", words=[
            WordSegment(text="ball", start=1.0, end=1.4,
                         probability=0.9, language="en"),
            WordSegment(text="ball", start=1.5, end=2.0,
                         probability=0.9, language="en"),
        ]),
    ]
    chat = utterances_to_chat(utts, child_id="C1")
    assert "&-um" in chat
    assert "[/]" in chat


def test_formatter_unintelligible_threshold():
    utts = [UtteranceSegment(start=0.0, end=2.0, text="cookie",
                              speaker="CHI", language="en", words=[
        WordSegment(text="cookie", start=0.0, end=2.0,
                     probability=0.1, language="en")  # below threshold
    ])]
    chat = utterances_to_chat(utts, unintelligible_threshold=0.3)
    assert "xxx" in chat


def test_formatter_zero_vocalization_marker():
    utts = [
        UtteranceSegment(start=0.0, end=1.0, text="hi", speaker="CHI",
                          language="en", words=[WordSegment(
            text="hi", start=0.0, end=1.0, probability=0.9, language="en")]),
        # Long gap > 5s, then another CHI -> should insert *CHI: 0 .
        UtteranceSegment(start=10.0, end=11.0, text="bye", speaker="CHI",
                          language="en", words=[WordSegment(
            text="bye", start=10.0, end=11.0, probability=0.9, language="en")]),
    ]
    chat = utterances_to_chat(utts, child_id="C1")
    assert "*CHI:\t0 ." in chat


def test_thai_word_spacing():
    u = UtteranceSegment(start=0.0, end=2.0, text="สวัสดีครับคุณแม่", speaker="CHI", language="th")
    # Once processed, "สวัสดีครับคุณแม่" should become space-separated words
    from src.audio_pipeline.chat_formatter import _render_utterance_body
    body = _render_utterance_body(u, unintelligible_threshold=0.3)
    assert "สวัสดี" in body
    assert " " in body


def test_thai_word_spacing_with_timings():
    words = [
        WordSegment(text="สวัสดีครับ", start=0.0, end=1.0, probability=0.9, language="th"),
        WordSegment(text="คุณแม่", start=1.5, end=2.5, probability=0.9, language="th")
    ]
    u = UtteranceSegment(start=0.0, end=3.0, text="สวัสดีครับคุณแม่", speaker="CHI", language="th", words=words)
    from src.audio_pipeline.chat_formatter import _render_utterance_body
    body = _render_utterance_body(u, unintelligible_threshold=0.3)
    assert "สวัสดี" in body
    assert "ครับ" in body
    assert "คุณแม่" in body
    # Verify spaces are inserted
    assert "สวัสดี ครับ คุณแม่" in body


# ----------------------------------------------------------------------
# CHATTER auto_fix
# ----------------------------------------------------------------------
def test_auto_fix_strips_trailing_whitespace():
    text = "@UTF8\n*CHI:\thello   \n@End\n"
    fixed, n = auto_fix(text)
    assert "hello   " not in fixed
    assert n >= 1


def test_auto_fix_adds_missing_terminator():
    text = "@UTF8\n@Begin\n*CHI:\thello world\n*MOT:\thi\n@End\n"
    fixed, n = auto_fix(text)
    assert "hello world ." in fixed
    assert "hi ." in fixed
    assert n >= 2


def test_auto_fix_idempotent():
    text = "@UTF8\n@Begin\n*CHI:\thello .\n@End\n"
    fixed, n = auto_fix(text)
    assert n == 0
    assert fixed.strip() == text.strip()


# ----------------------------------------------------------------------
# OpenAI Whisper API mapping
# ----------------------------------------------------------------------
def test_openai_api_mapping():
    # Mock response details
    raw_segments = [
        {
            "start": 0.0,
            "end": 2.0,
            "text": "สวัสดีครับ",
            "avg_logprob": -0.25,
            "no_speech_prob": 0.05,
            "words": [
                {"word": "สวัสดี", "start": 0.0, "end": 1.2, "probability": 0.95},
                {"word": "ครับ", "start": 1.2, "end": 2.0, "probability": 0.92}
            ]
        }
    ]
    # Verify that we can instantiate and parse these correctly.
    assert len(raw_segments) == 1

    from unittest.mock import patch, MagicMock
    import tempfile
    import os

    # 1. Test object-like response segments mapping
    mock_client_instance = MagicMock()
    mock_response = MagicMock()
    mock_response.language = "th"
    
    mock_seg = MagicMock()
    mock_seg.start = 0.0
    mock_seg.end = 2.0
    mock_seg.text = "สวัสดีครับ"
    mock_seg.avg_logprob = -0.25
    mock_seg.no_speech_prob = 0.05
    
    mock_word1 = MagicMock()
    mock_word1.word = "สวัสดี"
    mock_word1.start = 0.0
    mock_word1.end = 1.2
    mock_word1.probability = 0.95
    
    mock_word2 = MagicMock()
    mock_word2.word = "ครับ"
    mock_word2.start = 1.2
    mock_word2.end = 2.0
    mock_word2.probability = 0.92
    
    mock_seg.words = [mock_word1, mock_word2]
    mock_response.segments = [mock_seg]
    
    mock_client_instance.audio.transcriptions.create.return_value = mock_response

    with patch("src.audio_pipeline.whisper_transcribe._OpenAIClient", return_value=mock_client_instance), \
         patch.dict(os.environ, {"OPENAI_API_KEY": "fake_key"}), \
         tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        
        tmp_name = tmp.name
        tmp.write(b"fake audio content")
        tmp.close()
        
        try:
            transcriber = WhisperTranscriber(strategy="api_openai")
            segments = transcriber.transcribe(tmp_name)
            
            assert len(segments) == 1
            seg = segments[0]
            assert seg.start == 0.0
            assert seg.end == 2.0
            assert seg.text == "สวัสดีครับ"
            assert seg.avg_logprob == -0.25
            assert seg.no_speech_prob == 0.05
            assert seg.language == "th"
            
            assert len(seg.words) == 2
            assert seg.words[0].text == "สวัสดี"
            assert seg.words[0].start == 0.0
            assert seg.words[0].end == 1.2
            assert seg.words[0].probability == 0.95
            assert seg.words[0].language == "th"
            
            assert seg.words[1].text == "ครับ"
            assert seg.words[1].start == 1.2
            assert seg.words[1].end == 2.0
            assert seg.words[1].probability == 0.92
            assert seg.words[1].language == "th"
        finally:
            if os.path.exists(tmp_name):
                os.remove(tmp_name)

    # 2. Test dict-like response segments mapping
    mock_response_dict = MagicMock()
    mock_response_dict.language = "th"
    mock_response_dict.segments = raw_segments
    mock_client_instance.audio.transcriptions.create.return_value = mock_response_dict

    with patch("src.audio_pipeline.whisper_transcribe._OpenAIClient", return_value=mock_client_instance), \
         patch.dict(os.environ, {"OPENAI_API_KEY": "fake_key"}), \
         tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        
        tmp_name = tmp.name
        tmp.write(b"fake audio content")
        tmp.close()
        
        try:
            transcriber = WhisperTranscriber(strategy="api_openai")
            segments = transcriber.transcribe(tmp_name)
            
            assert len(segments) == 1
            seg = segments[0]
            assert seg.start == 0.0
            assert seg.end == 2.0
            assert seg.text == "สวัสดีครับ"
            assert seg.avg_logprob == -0.25
            assert seg.no_speech_prob == 0.05
            assert seg.language == "th"
            
            assert len(seg.words) == 2
            assert seg.words[0].text == "สวัสดี"
            assert seg.words[0].start == 0.0
            assert seg.words[0].end == 1.2
            assert seg.words[0].probability == 0.95
            assert seg.words[0].language == "th"
            
            assert seg.words[1].text == "ครับ"
            assert seg.words[1].start == 1.2
            assert seg.words[1].end == 2.0
            assert seg.words[1].probability == 0.92
            assert seg.words[1].language == "th"
        finally:
            if os.path.exists(tmp_name):
                os.remove(tmp_name)


def test_openai_api_fallback():
    from unittest.mock import patch, MagicMock
    import tempfile
    import os

    # Ensure no API key in environment
    with patch.dict(os.environ, {}, clear=True):
        transcriber = WhisperTranscriber(strategy="api_openai")
        
        # Mock local model loading and transcription to avoid downloading model files
        mock_model = MagicMock()
        mock_info = MagicMock()
        mock_info.language = "th"
        mock_local_seg = MagicMock()
        mock_local_seg.start = 0.0
        mock_local_seg.end = 1.0
        mock_local_seg.text = "สวัสดี"
        mock_local_seg.avg_logprob = -0.1
        mock_local_seg.no_speech_prob = 0.01
        mock_local_seg.words = []
        
        mock_model.transcribe.return_value = ([mock_local_seg], mock_info)
        
        with patch.object(transcriber, "_load", return_value=mock_model), \
             tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            
            tmp_name = tmp.name
            tmp.write(b"fake audio content")
            tmp.close()
            
            try:
                segments = transcriber.transcribe(tmp_name, vad_filter=False)
                assert transcriber.strategy == "auto"
                assert len(segments) == 1
                assert segments[0].text == "สวัสดี"
            finally:
                if os.path.exists(tmp_name):
                    os.remove(tmp_name)


def test_openai_api_error_fallback():
    from unittest.mock import patch, MagicMock
    import tempfile
    import os

    # Force OpenAI client to raise an exception
    with patch.dict(os.environ, {"OPENAI_API_KEY": "fake_key"}):
        transcriber = WhisperTranscriber(strategy="api_openai")
        
        # Mock local model loading and transcription to avoid downloading model files
        mock_model = MagicMock()
        mock_info = MagicMock()
        mock_info.language = "th"
        mock_local_seg = MagicMock()
        mock_local_seg.start = 0.0
        mock_local_seg.end = 1.0
        mock_local_seg.text = "สวัสดี"
        mock_local_seg.avg_logprob = -0.1
        mock_local_seg.no_speech_prob = 0.01
        mock_local_seg.words = []
        
        mock_model.transcribe.return_value = ([mock_local_seg], mock_info)
        
        # Mock OpenAI to raise an exception
        mock_openai = MagicMock()
        mock_openai.side_effect = Exception("Connection timed out")
        
        with patch("src.audio_pipeline.whisper_transcribe._OpenAIClient", mock_openai), \
             patch.object(transcriber, "_load", return_value=mock_model), \
             tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            
            tmp_name = tmp.name
            tmp.write(b"fake audio content")
            tmp.close()
            
            try:
                segments = transcriber.transcribe(tmp_name, vad_filter=False)
                assert transcriber.strategy == "auto"
                assert len(segments) == 1
                assert segments[0].text == "สวัสดี"
            finally:
                if os.path.exists(tmp_name):
                    os.remove(tmp_name)



# ----------------------------------------------------------------------
# Context-aware diarization fallback
# ----------------------------------------------------------------------
def test_contextual_diarization_fallback():
    from unittest.mock import patch, MagicMock
    import numpy as np
    from src.audio_pipeline.diarization import EmbeddingDiarizer, EmbeddingDiarizerConfig
    from src.audio_pipeline.whisper_transcribe import UtteranceSegment

    # Case 1: F0 is None -> falls back to context
    config = EmbeddingDiarizerConfig()
    diarizer = EmbeddingDiarizer(config=config)

    # Mock _embed_clip to return embeddings for first and third segments, and None for the second
    mock_embeddings = [
        np.array([1.0, 0.0]),  # Utterance 1
        None,                  # Utterance 2 (short)
        np.array([1.0, 0.0]),  # Utterance 3
    ]
    diarizer._embed_clip = MagicMock(side_effect=mock_embeddings)

    # Mock _median_f0 to return None for second segment and 250.0 (high/child-like) for others
    diarizer._pitch._median_f0 = MagicMock(side_effect=[250.0, None, 250.0])

    # Construct UtteranceSegments
    utterances = [
        UtteranceSegment(start=0.0, end=1.0, text="hello", speaker=None),
        UtteranceSegment(start=1.1, end=1.3, text="yes", speaker=None),
        UtteranceSegment(start=1.4, end=2.4, text="bye", speaker=None),
    ]

    dummy_signal = np.zeros(16000 * 3)
    with patch("librosa.load", return_value=(dummy_signal, 16000)):
        out = diarizer.assign("dummy_path.wav", utterances)

    # Check that:
    # 1. The first utterance got CHI
    # 2. The third utterance got CHI
    # 3. The second utterance (which had no embedding/pitch) got CHI via context
    assert out[0].speaker == "CHI"
    assert out[2].speaker == "CHI"
    assert out[1].speaker == "CHI"

    # Case 2: F0 is present -> uses pitch classification, even if neighboring context is present
    diarizer2 = EmbeddingDiarizer(config=config)
    mock_embeddings2 = [
        np.array([1.0, 0.0]),  # Utterance 1 (clusters to CHI)
        None,                  # Utterance 2 (short, has F0, should classify as MOT/ADULT based on low pitch)
        np.array([1.0, 0.0]),  # Utterance 3 (clusters to CHI)
    ]
    diarizer2._embed_clip = MagicMock(side_effect=mock_embeddings2)
    # Low F0 (100.0 Hz) for second segment (well below 230.0 Hz threshold)
    diarizer2._pitch._median_f0 = MagicMock(side_effect=[250.0, 100.0, 250.0])

    utterances2 = [
        UtteranceSegment(start=0.0, end=1.0, text="hello", speaker=None),
        UtteranceSegment(start=1.1, end=1.3, text="yes", speaker=None),
        UtteranceSegment(start=1.4, end=2.4, text="bye", speaker=None),
    ]

    with patch("librosa.load", return_value=(dummy_signal, 16000)):
        out2 = diarizer2.assign("dummy_path.wav", utterances2)

    assert out2[0].speaker == "CHI"
    assert out2[2].speaker == "CHI"
    assert out2[1].speaker == "MOT"  # default adult label when pitch is below threshold (F0 < 230.0 Hz)

    # Case 3: Right-only context fallback (first segment has no cluster/F0, second is CHI)
    diarizer3 = EmbeddingDiarizer(config=config)
    mock_embeddings3 = [
        None,                  # Utterance 1 (short, F0 None, emb None)
        np.array([1.0, 0.0]),  # Utterance 2 (CHI)
        np.array([1.0, 0.0]),  # Utterance 3 (CHI)
    ]
    diarizer3._embed_clip = MagicMock(side_effect=mock_embeddings3)
    diarizer3._pitch._median_f0 = MagicMock(side_effect=[None, 250.0, 250.0])

    utterances3 = [
        UtteranceSegment(start=0.0, end=0.3, text="short", speaker=None),
        UtteranceSegment(start=0.4, end=1.4, text="hello", speaker=None),
        UtteranceSegment(start=1.5, end=2.5, text="bye", speaker=None),
    ]

    with patch("librosa.load", return_value=(dummy_signal, 16000)):
        out3 = diarizer3.assign("dummy_path.wav", utterances3)

    assert out3[1].speaker == "CHI"
    assert out3[2].speaker == "CHI"
    assert out3[0].speaker == "CHI"  # should inherit CHI from right (Utterance 2)


# ----------------------------------------------------------------------
# Test Thai pronoun reversals and restricted interests
# ----------------------------------------------------------------------
def test_thai_clinical_features():
    from src.chat_feature_extractor import count_pronoun_reversals
    # Test Thai pronoun reversals
    assert count_pronoun_reversals("เธอกินข้าว") == 0 # no reversal
    assert count_pronoun_reversals("เธอจะไปหาหมอ (เมื่อพูดถึงตัวเอง)") > 0


# ----------------------------------------------------------------------
# Test runner
# ----------------------------------------------------------------------
def main() -> int:
    tests = [v for k, v in globals().items()
              if k.startswith("test_") and callable(v)]
    passed = 0
    failed = []
    for t in tests:
        try:
            t()
            print(f"  ✓ {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  ✗ {t.__name__}: {e}")
            failed.append(t.__name__)
        except Exception as e:  # noqa: BLE001
            print(f"  ✗ {t.__name__}: {type(e).__name__}: {e}")
            failed.append(t.__name__)
    print(f"\n{passed}/{len(tests)} passed")
    if failed:
        print("Failed:", ", ".join(failed))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

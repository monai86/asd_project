from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import textwrap

import numpy as np
import pytest
import soundfile as sf


FIFTEEN_MINUTES_SECONDS = 15 * 60
SOURCE_SAMPLE_RATE_HZ = 48_000
TARGET_SAMPLE_RATE_HZ = 16_000
PEAK_RSS_CEILING_BYTES = 512 * 1024 * 1024


@pytest.mark.audio
@pytest.mark.slow
def test_fifteen_minute_48khz_stereo_normalization_peak_rss(
    tmp_path: Path,
) -> None:
    """Evidence that the maximum decoded v1.7 workload stays memory-bounded.

    A 15-minute float64 stereo full read alone would occupy about 659 MiB,
    before mono and resampled arrays. The 512 MiB process ceiling therefore
    rejects that design while allowing the pinned runtime/import baseline and
    fixed-size streaming blocks. The synthetic MP3 remains within the 100 MiB
    intake limit and is generated outside the repository.
    """

    source_path = tmp_path / "fifteen-minute-48khz-stereo.mp3"
    normalized_path = tmp_path / "normalized.wav"
    repeated_path = tmp_path / "normalized-repeated.wav"
    frame = np.arange(SOURCE_SAMPLE_RATE_HZ, dtype=np.float32)
    one_second = np.column_stack(
        (
            0.1 * np.sin(2 * np.pi * 220 * frame / SOURCE_SAMPLE_RATE_HZ),
            0.1 * np.sin(2 * np.pi * 330 * frame / SOURCE_SAMPLE_RATE_HZ),
        )
    ).astype(np.float32)
    with sf.SoundFile(
        source_path,
        mode="w",
        samplerate=SOURCE_SAMPLE_RATE_HZ,
        channels=2,
        format="MP3",
        subtype="MPEG_LAYER_III",
    ) as writer:
        for _ in range(FIFTEEN_MINUTES_SECONDS):
            writer.write(one_second)

    assert source_path.stat().st_size <= 100 * 1024 * 1024
    script = textwrap.dedent(
        """
        import json
        from pathlib import Path
        import resource
        import sys
        import time

        from app.services.audio_media_service import normalize_audio, probe_audio

        source_path = Path(sys.argv[1])
        destination_path = Path(sys.argv[2])
        started = time.perf_counter()
        with source_path.open("rb") as source:
            decoded = probe_audio(source)
            with destination_path.open("w+b") as destination:
                normalized = normalize_audio(
                    source,
                    destination,
                    decoded=decoded,
                    target_sample_rate_hz=16_000,
                )
        usage = resource.getrusage(resource.RUSAGE_SELF)
        peak_rss_bytes = (
            usage.ru_maxrss
            if sys.platform == "darwin"
            else usage.ru_maxrss * 1024
        )
        print(json.dumps({
            "decoded_duration_ms": decoded.duration_ms,
            "decoded_frame_count": decoded.frame_count,
            "normalized_frame_count": normalized.frame_count,
            "normalized_checksum_sha256": normalized.normalized_checksum_sha256,
            "peak_rss_bytes": peak_rss_bytes,
            "cpu_seconds": usage.ru_utime + usage.ru_stime,
            "elapsed_seconds": time.perf_counter() - started,
            "conversion_profile": normalized.conversion_profile,
        }))
        """
    )
    completed = subprocess.run(
        [sys.executable, "-c", script, str(source_path), str(normalized_path)],
        cwd=Path(__file__).resolve().parents[1],
        check=True,
        capture_output=True,
        text=True,
    )
    evidence = json.loads(completed.stdout)
    repeated = subprocess.run(
        [sys.executable, "-c", script, str(source_path), str(repeated_path)],
        cwd=Path(__file__).resolve().parents[1],
        check=True,
        capture_output=True,
        text=True,
    )
    repeated_evidence = json.loads(repeated.stdout)
    print(
        json.dumps(
            {
                "first": evidence,
                "repeated": repeated_evidence,
            },
            sort_keys=True,
        )
    )

    assert evidence["decoded_duration_ms"] == 900_000
    assert evidence["decoded_frame_count"] == (
        FIFTEEN_MINUTES_SECONDS * SOURCE_SAMPLE_RATE_HZ
    )
    assert evidence["normalized_frame_count"] == (
        FIFTEEN_MINUTES_SECONDS * TARGET_SAMPLE_RATE_HZ
    )
    assert repeated_evidence["normalized_frame_count"] == (
        evidence["normalized_frame_count"]
    )
    assert repeated_evidence["normalized_checksum_sha256"] == (
        evidence["normalized_checksum_sha256"]
    )
    assert evidence["peak_rss_bytes"] < PEAK_RSS_CEILING_BYTES
    assert repeated_evidence["peak_rss_bytes"] < PEAK_RSS_CEILING_BYTES
    assert evidence["cpu_seconds"] > 0
    assert evidence["elapsed_seconds"] > 0
    assert "streaming_block_frames=" in evidence["conversion_profile"]
    assert "overlap_frames=" in evidence["conversion_profile"]

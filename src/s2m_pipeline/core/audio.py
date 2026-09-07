"""Audio extraction and enhancement from the source video, via FFmpeg."""

from __future__ import annotations

import subprocess
from pathlib import Path


def extract_audio(video_path: Path, output_wav_path: Path, sample_rate: int = 16000) -> Path:
    """Extract mono PCM audio at `sample_rate` Hz, suitable for ASR models."""
    output_wav_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-vn",
        "-ac",
        "1",
        "-ar",
        str(sample_rate),
        "-c:a",
        "pcm_s16le",
        str(output_wav_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg audio extraction failed:\n{result.stderr}")

    return output_wav_path


def enhance_audio(input_wav_path: Path, output_wav_path: Path) -> Path:
    """Denoise and loudness-normalize the master audio (CPU-only, FFmpeg built-ins).

    Applied once to the master audio right after extraction, so both
    transcription and the original-voice narration clips (section 6.2,
    option 1 of the cahier des charges) benefit from cleaner input:
      - afftdn: FFT-based noise reduction (removes steady background hiss/hum)
      - loudnorm: EBU R128 loudness normalization (-16 LUFS, standard for
        spoken-word content) so volume is consistent across the recording
    """
    output_wav_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_wav_path),
        "-af",
        "afftdn=nf=-25,loudnorm=I=-16:TP=-1.5:LRA=11",
        # loudnorm's internal resampling defaults to 192 kHz if not pinned,
        # which is pure waste for 16 kHz speech (12x file size, no audible
        # benefit) - force the output back to the input rate.
        "-ar",
        "16000",
        str(output_wav_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg audio enhancement failed:\n{result.stderr}")

    return output_wav_path


def extract_clip(audio_path: Path, start: float, end: float, output_path: Path) -> Path:
    """Extract a single [start, end] slice of audio (for original-voice narration)."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(audio_path),
        "-ss",
        str(start),
        "-to",
        str(end),
        "-c",
        "copy",
        str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg clip extraction failed:\n{result.stderr}")

    return output_path


def concat_clips(clip_paths: list[Path], output_path: Path) -> Path:
    """Concatenate several audio clips (same codec) into one file, in order."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    list_file = output_path.with_suffix(".concat.txt")
    list_file.write_text(
        "\n".join(f"file '{p.resolve().as_posix()}'" for p in clip_paths), encoding="utf-8"
    )

    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(list_file),
        "-c",
        "copy",
        str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    list_file.unlink(missing_ok=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg concat failed:\n{result.stderr}")

    return output_path


def audio_duration_seconds(audio_path: Path) -> float:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(audio_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed:\n{result.stderr}")
    return float(result.stdout.strip())


def to_wav(input_path: Path, output_wav_path: Path, sample_rate: int = 16000) -> Path:
    """Transcode any audio file to the WAV the renderer expects.

    Speech synthesis returns MP3, while the Remotion compositions load
    `audio/<scene>.wav`. Converting here keeps that contract in one place
    rather than teaching the renderer a second format.
    """
    output_wav_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", str(input_path),
            "-vn", "-acodec", "pcm_s16le",
            "-ar", str(sample_rate), "-ac", "1",
            str(output_wav_path),
        ],
        check=True,
    )
    return output_wav_path

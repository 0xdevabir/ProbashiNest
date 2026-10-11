"""Measure Bangla speech-to-text word error rate (WER) on your own recordings.

Usage:
    python -m probashi.voice.eval recordings/
    python -m probashi.voice.eval recordings/ --provider azure

Layout: one sub-folder per accent, each clip next to a .txt file with the
exact words spoken (UTF-8 Bangla):

    recordings/
      standard/     clip01.ogg  clip01.txt  ...
      sylheti/      clip01.webm clip01.txt  ...
      chittagonian/ ...
      noakhali/     ...

See README.md for how to record the clips. `recordings/` is git-ignored.
"""
from __future__ import annotations

import argparse
import mimetypes
import os
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

AUDIO_SUFFIXES = {".ogg", ".opus", ".oga", ".webm", ".wav", ".mp3", ".m4a", ".mp4", ".flac"}
_BN_DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")


def normalize(text: str) -> list[str]:
    """Lower-case, drop punctuation, unify digits, split into words."""
    text = unicodedata.normalize("NFC", text).translate(_BN_DIGITS).lower()
    # \w does not cover Bangla vowel signs (category Mc/Mn), so keep marks.
    cleaned = "".join(
        ch if unicodedata.category(ch)[0] in "LMN" or ch.isspace() else " "
        for ch in text
    )
    return cleaned.split()


def edit_distance(ref: list[str], hyp: list[str]) -> int:
    """Word-level Levenshtein distance."""
    prev = list(range(len(hyp) + 1))
    for i, r in enumerate(ref, 1):
        cur = [i]
        for j, h in enumerate(hyp, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (r != h)))
        prev = cur
    return prev[-1]


def wer(reference: str, hypothesis: str) -> float:
    """Word error rate of one pair. 0.0 is perfect; can exceed 1.0."""
    ref, hyp = normalize(reference), normalize(hypothesis)
    if not ref:
        raise ValueError("Reference transcript is empty")
    return edit_distance(ref, hyp) / len(ref)


def find_clips(folder: Path) -> list[tuple[Path, Path]]:
    """(audio, reference .txt) pairs; clips without a .txt are skipped."""
    pairs = []
    for audio in sorted(folder.rglob("*")):
        if audio.suffix.lower() in AUDIO_SUFFIXES and audio.with_suffix(".txt").exists():
            pairs.append((audio, audio.with_suffix(".txt")))
    return pairs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("folder", type=Path)
    parser.add_argument("--provider", help="override VOICE_STT_PROVIDER for this run")
    parser.add_argument("--show", action="store_true", help="print each transcript")
    args = parser.parse_args(argv)

    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass
    if args.provider:
        os.environ["VOICE_STT_PROVIDER"] = args.provider
        os.environ["VOICE_FALLBACK"] = "false"  # measure one provider at a time

    from . import VoiceError, transcribe_bn

    clips = find_clips(args.folder)
    if not clips:
        print(f"No audio clips with matching .txt files under {args.folder}")
        return 1

    # accent -> [errors, reference words]
    totals: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    failed = 0
    for audio, ref_path in clips:
        accent = audio.parent.name if audio.parent != args.folder else "(none)"
        reference = ref_path.read_text(encoding="utf-8")
        mime = mimetypes.guess_type(audio.name)[0] or "application/octet-stream"
        try:
            hypothesis = transcribe_bn(audio.read_bytes(), mime)
        except VoiceError as e:
            failed += 1
            print(f"FAILED  {audio.relative_to(args.folder)}  {type(e).__name__}: {e}")
            continue
        ref_words = normalize(reference)
        if not ref_words:
            print(f"SKIPPED {audio.relative_to(args.folder)}  empty reference")
            continue
        errors = edit_distance(ref_words, normalize(hypothesis))
        totals[accent][0] += errors
        totals[accent][1] += len(ref_words)
        print(f"{errors / len(ref_words):6.1%}  {audio.relative_to(args.folder)}")
        if args.show:
            print(f"        ref: {reference.strip()}\n        hyp: {hypothesis}")

    print("\nWER by accent (total word errors / total reference words)")
    all_errors = all_words = 0
    for accent, (errors, words) in sorted(totals.items()):
        print(f"  {accent:<16} {errors / words:6.1%}  ({words} words)")
        all_errors += errors
        all_words += words
    if all_words:
        print(f"  {'OVERALL':<16} {all_errors / all_words:6.1%}  ({all_words} words)")
    print(f"provider={os.getenv('VOICE_STT_PROVIDER') or 'default'}  "
          f"clips={len(clips)}  failed={failed}")
    return 0 if all_words else 1


if __name__ == "__main__":
    sys.exit(main())

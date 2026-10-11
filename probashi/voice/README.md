# probashi.voice — Bangla speech in and out (Agent 4)

```python
from probashi.voice import transcribe_bn, synthesize_bn, VoiceError

text = transcribe_bn(audio_bytes, "audio/webm")   # Bangla text
mp3 = synthesize_bn("ফি 500000 BDT")              # says "ফি পাঁচ লাখ টাকা"
```

Provider choice and the research behind it are in [PROVIDERS.md](PROVIDERS.md).

## Setup

1. Install `ffmpeg` (`brew install ffmpeg`, or `apt-get install -y ffmpeg` in the Docker image). It is the only requirement beyond the Python standard library.
2. Copy the voice block from `.env.example` into `.env` and fill in the keys.
3. Run the tests: `pytest probashi/voice`

## Environment variables

| Variable | Default | Meaning |
| --- | --- | --- |
| `VOICE_STT_PROVIDER` | `elevenlabs` | Speech-to-text: `elevenlabs` or `azure` |
| `VOICE_TTS_PROVIDER` | `azure` | Text-to-speech: `azure` or `elevenlabs` |
| `VOICE_FALLBACK` | `true` | If the chosen provider fails, try the other one when its keys are set |
| `ELEVENLABS_API_KEY` | — | Needed for ElevenLabs |
| `ELEVENLABS_VOICE_ID` | — | Needed for ElevenLabs text-to-speech only. No default: the team must pick a voice |
| `AZURE_SPEECH_KEY`, `AZURE_SPEECH_REGION` | — | Needed for Azure |
| `AZURE_SPEECH_ENDPOINT` | regional host | Optional resource endpoint for Azure speech-to-text |
| `AZURE_TTS_VOICE` | `bn-BD-NabanitaNeural` | Azure voice |
| `AZURE_TTS_RATE` | `-15%` | Slower speech for older listeners |
| `ELEVENLABS_TTS_SPEED` | `0.9` | Below 1.0 is slower |
| `VOICE_STT_TIMEOUT_SECONDS` / `VOICE_TTS_TIMEOUT_SECONDS` | `30` / `20` | Per attempt |
| `VOICE_TTS_MAX_CHARS` | `540` | Length cap for spoken text |
| `FFMPEG_BINARY` | found on `PATH` | Path to ffmpeg |

With only one vendor's keys set, both directions still work through that vendor.

## Errors the backend can catch

Everything raised is a `VoiceError`, so one `except VoiceError` keeps the verdict flowing when voice fails.

| Exception | When | Suggested handling |
| --- | --- | --- |
| `AudioTooLongError` | Recording over 2 minutes or upload over 25 MB | Ask for a shorter recording |
| `NoSpeechError` | Provider heard nothing | Ask the user to speak again |
| `AudioError` (parent of the two above) | Empty, corrupt, under 0.3 s, or not audio | Ask the user to record again |
| `ProviderError` | Timeout, network, quota, bad key. Has `.provider`, `.status`, `.retryable` | Return the verdict without audio |
| `VoiceConfigError` | Missing keys, unknown provider name, ffmpeg missing | Deployment problem; log it |

Each provider call gets one retry on timeouts, connection errors and HTTP 408/429/5xx. After that the fallback provider is tried the same way.

## Text preparation for speech

`synthesize_bn` runs `prepare_tts_text` first:

- Numbers become Bangla words with lakh/crore grouping: `1250000` → `বারো লাখ পঞ্চাশ হাজার`. Bangla digits and comma grouping are accepted.
- Currency codes become names, in either order: `500000 BDT`, `BDT 500000`, `৳500`, `Tk`, `SAR`, `AED`, `QAR`, `KWD`, `OMR`, `BHD`, `MYR`/`RM`, `SGD`, `USD`/`$`.
- Phone-like numbers (starting with `0` or `+`, or 9+ digits) and codes such as `RL-0123` are read digit by digit.
- `%` becomes `শতাংশ`. Markdown symbols are removed.
- Text is cut at a sentence boundary to about 45 seconds.

Things callers should know:

- **Short codes are ambiguous.** A five-digit helpline number looks like an amount and would be read as one. Wrap those with `probashi.voice.text_prep.spell_digits("...")` before passing the text in.
- **Truncation is silent apart from the length.** Put the verdict and the most important step first, because anything past the cap is dropped.
- The module does not rewrite long sentences. Write short ones upstream.

## Limits

- Input audio: 2 minutes, 25 MB. Formats: anything ffmpeg can decode from a pipe, which covers browser webm/ogg (Opus), WhatsApp ogg/opus, wav and mp3.
- iPhone Safari recordings (`audio/mp4`) may fail when the file is not a fragmented MP4, because audio is piped through ffmpeg in memory and never written to disk. Not tested on a real iPhone.
- The 45-second cap rests on an assumed 12 characters per second for slow Bangla speech. This was not measured. Time a few real outputs and adjust `VOICE_TTS_MAX_CHARS`.
- Output is mp3 at 24 kHz / 48 kbps mono from Azure (about 6 KB per second, friendly to slow connections) and 44.1 kHz / 128 kbps from ElevenLabs.
- Audio and transcripts are never written to disk or logged. Logs contain only provider name, duration, attempt and HTTP status.
- Recordings are sent to third-party speech services. See the privacy note in PROVIDERS.md.

## Costs (assumptions, not quotes)

Assuming one check is 30 seconds of speech in and 400 characters spoken back:

| Step | Provider | Assumed rate | Per check | Per 1,000 checks |
| --- | --- | --- | --- | --- |
| Speech-to-text | ElevenLabs Scribe v2 | $0.22 per hour | $0.0018 | about $1.83 |
| Text-to-speech | ElevenLabs Eleven v3 (fallback) | $0.08 per 1,000 characters | $0.032 | $32 |
| Text-to-speech | Azure neural (default) | not verified | — | first 0.5 M characters per month are free, about 1,250 checks |

Azure's paid rate could not be read from its pricing page, so check it before budgeting. ElevenLabs text-to-speech is the expensive path; keep Azure as the default.

## Accents

**No accent has been tested yet.** There were no API keys and no recordings when this was built, so there are no results to report for Sylheti, Chittagonian or Noakhali speech. None of the providers documents support for these varieties; all of them treat Bangla as one language (or `bn-IN` / `bn-BD`). Expect standard Bangla to do best and strong regional speech to do noticeably worse until measured.

Fill this table in after running the evaluation:

| Accent | Clips | WER, ElevenLabs | WER, Azure | Notes |
| --- | --- | --- | --- | --- |
| Standard (Dhaka) | | | | |
| Sylheti | | | | |
| Chittagonian | | | | |
| Noakhali | | | | |

### Recording the test clips (10 per person)

1. Each team member records 10 clips in the accent they speak natively. Say which accent it is; do not imitate one.
2. Record the way a user would: on a phone, as a WhatsApp voice note or with the app's record button, in a normal room. Do not use a studio microphone. Keep each clip between 5 and 20 seconds.
3. Speak naturally, not as if reading. Use sentences a worker would say. Cover these across the 10 clips: a destination country, a job title, a monthly salary with a number, a fee in taka, an agency name, a contract length, and two free-form questions.
4. Use invented details only. No real passport numbers, phone numbers or agency names.
5. For each clip, write exactly what was said, in Bangla script, in a `.txt` file with the same name. Write the regional words as spoken, not the standard-Bangla equivalent. Write numbers the same way in every file.
6. Put the files in one folder per accent:

   ```
   recordings/
     standard/      rahim_01.ogg  rahim_01.txt ...
     sylheti/
     chittagonian/
     noakhali/
   ```

   `recordings/` is git-ignored. Do not commit the clips.

7. Run it once per provider:

   ```bash
   python -m probashi.voice.eval recordings/ --provider elevenlabs
   python -m probashi.voice.eval recordings/ --provider azure --show
   ```

The script prints word error rate per clip, per accent and overall. WER counts a regional spelling that differs from the reference as an error even when the meaning is right, so read the `--show` output before judging a provider. What matters for this product is whether the key facts (country, salary, fee, agency) survive.

## Files

| File | Purpose |
| --- | --- |
| `__init__.py` | `transcribe_bn`, `synthesize_bn`, provider choice, retry and fallback |
| `audio.py` | ffmpeg conversion to 16 kHz mono WAV, length checks |
| `text_prep.py` | Number and currency expansion, truncation |
| `providers/` | `base.py` interface, `elevenlabs.py`, `azure.py` |
| `eval.py` | WER evaluation script |
| `errors.py` | Exception types |
| `tests/` | `pytest probashi/voice`; live tests skip without keys, conversion tests skip without ffmpeg |

## Status

Done: both functions, two providers per direction, conversion, text preparation, evaluation script, tests.

Not verified against live services: no keys were available, so the four live tests have never run. Request shapes follow the official API references and are unit-tested with HTTP mocked.

Open questions:

- `ffmpeg` must be installed in the backend Docker image (Agent 1).
- Which ElevenLabs voice to use, if that fallback is wanted.
- Is sending recordings to ElevenLabs and Azure acceptable, and does the consent text say so?
- Google Chirp is the only speech-to-text with a documented `bn-BD` locale. Add it if accent results are poor.

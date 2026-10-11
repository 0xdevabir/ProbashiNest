# Bangla speech providers: comparison and recommendation

Checked on 2026-10-11 against the official pages linked below. Nothing here
was measured by us: no API keys were available, so accuracy and latency are
either the vendor's own claim or marked **not verified**. Run
`python -m probashi.voice.eval` on real clips before trusting any row.

## Recommendation

| Direction | Recommended | Fallback | Why |
| --- | --- | --- | --- |
| Speech-to-text | ElevenLabs Scribe v2 | Azure fast transcription (`bn-IN`) | Scribe lists Bengali in its ≤10% WER tier, accepts our audio in one REST call with one API key, and is the cheapest option found. Azure is the fallback because the same key already serves text-to-speech. |
| Text-to-speech | Azure neural voice `bn-BD-NabanitaNeural` | ElevenLabs Eleven v3 | Azure is the only provider found with documented, generally available Bangladesh-locale voices plus a documented speaking-rate control (SSML `prosody rate`) and direct mp3 output. |

Two vendors, each able to do both directions, so one outage or one missing
key does not take voice down.

**This choice is provisional.** The strongest alternative for speech-to-text
is Google Chirp, the only service found that documents a `bn-BD`
speech-to-text locale. It was not chosen as the default only because it needs
a Google Cloud project and service-account credentials rather than a single
key. If the accent evaluation shows Scribe struggling, add Google next: the
provider interface in `providers/base.py` makes that one new file.

## Speech-to-text

| Provider | Bangla support (from docs) | Accuracy notes | Cost | Runs on AWS? |
| --- | --- | --- | --- | --- |
| **ElevenLabs Scribe v2** | "Bengali (ben)" listed. No separate Bangladesh/India locale. [docs](https://elevenlabs.io/docs/overview/capabilities/speech-to-text) | Vendor places Bengali in its "High Accuracy" tier, >5% to ≤10% WER. Vendor benchmark, not ours. | $0.22 per audio hour. [pricing](https://elevenlabs.io/pricing/api) | Called over HTTPS from AWS. Not an AWS service. |
| **Azure fast transcription** | `bn-IN` only. No `bn-BD` row in the speech-to-text table. [docs](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support?tabs=stt) | None published per language. | Not verified: the pricing page did not render prices. Free tier: 5 audio hours per month. [pricing](https://azure.microsoft.com/en-us/pricing/details/cognitive-services/speech-services/) | Called over HTTPS from AWS. |
| **Google Cloud Speech-to-Text v2 (Chirp 2 / Chirp 3)** | `bn-BD` and `bn-IN` both listed. Chirp 2 in `asia-southeast1` and `europe-west4`, Chirp 3 in `eu`. [docs](https://docs.cloud.google.com/speech-to-text/v2/docs/speech-to-text-supported-languages) | None published per language. | Not verified from the official page. Secondary sources say about $0.016 per minute. [pricing](https://cloud.google.com/speech-to-text/pricing) | Called over HTTPS from AWS; needs Google service-account credentials. |
| **Amazon Transcribe** | `bn-IN` only, batch and streaming. [docs](https://docs.aws.amazon.com/transcribe/latest/dg/supported-languages.html) | None published per language. | $0.006 per minute batch, $0.01 per minute streaming (US East example rates). [pricing](https://aws.amazon.com/transcribe/pricing/) | Native AWS. Batch reads the file from S3, which conflicts with our rule not to store audio; streaming avoids that. |
| **OpenAI transcription API** | Not confirmed. The guide gives no language list on the page; it says Whisper "supports 98 languages, but accuracy varies by language". [docs](https://developers.openai.com/api/docs/guides/speech-to-text) | Not verified for Bangla. | Not checked. | Called over HTTPS from AWS. |
| **Whisper large-v3** (open source) | Model card tags 99 languages but does not name Bengali on the page. [model card](https://huggingface.co/openai/whisper-large-v3) | Card warns of "lower accuracy on low-resource and/or low-discoverability languages" and worse hallucination there. | Free model, Apache 2.0. You pay for a GPU. | Yes, self-hosted on a GPU instance. 1,550 M parameters. |
| **Meta MMS (`mms-1b-all`)** (open source) | `ben` is in the supported list. [model card](https://huggingface.co/facebook/mms-1b-all) | None for Bangla on the card. | Free model. | Technically yes, but the licence is CC-BY-NC 4.0 (non-commercial), which rules it out for a product. |

Latency was not measured for any provider.

## Text-to-speech

| Provider | Bangla support (from docs) | Rate control | Cost | Runs on AWS? |
| --- | --- | --- | --- | --- |
| **Azure neural TTS** | `bn-BD-NabanitaNeural`, `bn-BD-PradeepNeural`; also `bn-IN-TanishaaNeural`, `bn-IN-BashkarNeural`. [docs](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support?tabs=tts) | Yes, SSML `prosody rate`. mp3 output formats listed in the [REST reference](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/rest-text-to-speech). | Not verified: prices did not render. Free tier: 0.5 million characters per month. [pricing](https://azure.microsoft.com/en-us/pricing/details/cognitive-services/speech-services/) | Called over HTTPS from AWS. |
| **ElevenLabs Eleven v3** | "Bengali (ben)" in the v3 language list. Multilingual v2 and Flash v2.5 do **not** list Bengali. [models](https://elevenlabs.io/docs/overview/models), [TTS docs](https://elevenlabs.io/docs/overview/capabilities/text-to-speech) | `voice_settings.speed` exists in the API; whether v3 honours it is **not verified**. [API](https://elevenlabs.io/docs/api-reference/text-to-speech/convert) | $0.08 per 1,000 characters. [pricing](https://elevenlabs.io/pricing/api) | Called over HTTPS from AWS. |
| **Google Gemini TTS** | "Bangla (Bangladesh)", `bn-BD`, GA. [docs](https://docs.cloud.google.com/text-to-speech/docs/gemini-tts) | No documented API speed field; pace is steered by prompt and markup tags. mp3 for non-streaming requests. | Not verified. [pricing](https://cloud.google.com/text-to-speech/pricing) | Called over HTTPS from AWS; needs Google credentials. |
| **Google Cloud TTS (Chirp 3 HD, WaveNet, Standard)** | `bn-IN` voices only; no `bn-BD` voices on the page. [docs](https://docs.cloud.google.com/text-to-speech/docs/list-voices-and-types) | Not checked. | Not verified. | Same as above. |
| **Amazon Polly** | **No Bangla.** Bengali is absent from the language list. [docs](https://docs.aws.amazon.com/polly/latest/dg/supported-languages.html) | — | — | Native AWS, but unusable for us. |
| **AI4Bharat Indic Parler-TTS** (open source) | Bengali officially supported, about 140 hours of Bengali training speech. Indian Bengali, not Bangladesh-specific. [model card](https://huggingface.co/ai4bharat/indic-parler-tts) | Speaking rate is set through a text description of the voice. | Free model, Apache 2.0. You pay for a GPU. | Yes, self-hosted. 0.9 B parameters; no speed figures on the card. |
| **Meta MMS-TTS (`mms-tts-ben`)** (open source) | Bengali VITS checkpoint, 36 M parameters. [model card](https://huggingface.co/facebook/mms-tts-ben) | None documented. | Free model. | Small enough for CPU, but CC-BY-NC 4.0 (non-commercial). |

## What this means for AWS

Nothing AWS-native covers Bangla end to end: Polly has no Bangla voice and
Transcribe has only `bn-IN`. The backend can still run on AWS and call
ElevenLabs and Azure over HTTPS; the only local requirement is the `ffmpeg`
binary in the container image.

## Privacy note

Both recommended providers receive the user's voice recording. ElevenLabs'
zero-retention mode (`enable_logging=false`) is documented as enterprise-only,
so on a normal plan they may retain request data. The team should decide
whether that is acceptable and say so in the user-facing consent text.

## Not verified, to do

- Real WER on Bangladeshi speech, especially Sylheti, Chittagonian and Noakhali accents.
- Latency from the deployment region.
- Azure and Google prices in US dollars.
- Whether Eleven v3 honours `voice_settings.speed`.
- Which Azure regions offer fast transcription for `bn-IN`.

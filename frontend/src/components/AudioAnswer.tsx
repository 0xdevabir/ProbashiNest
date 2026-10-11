import { useEffect, useRef, useState } from 'react'
import { useI18n } from '../i18n'
import { SpeakerIcon, StopIcon } from './icons'

interface AudioAnswerProps {
  /** mp3 of the spoken answer from the API. */
  audioBase64: string | null
  /** Bangla text read by the phone's own voice when the API sent no audio. */
  fallbackText: string
}

function banglaVoice(): Promise<SpeechSynthesisVoice | null> {
  if (!('speechSynthesis' in window)) return Promise.resolve(null)
  const find = () => speechSynthesis.getVoices().find((voice) => voice.lang.startsWith('bn')) ?? null
  const found = find()
  if (found) return Promise.resolve(found)
  // Voices load asynchronously in Chrome; give them a moment, then give up.
  return new Promise((resolve) => {
    const done = () => resolve(find())
    speechSynthesis.addEventListener('voiceschanged', done, { once: true })
    setTimeout(done, 1500)
  })
}

/** Plays the answer as soon as the result appears, with a button to hear it again. */
export function AudioAnswer({ audioBase64, fallbackText }: AudioAnswerProps) {
  const { t } = useI18n()
  const [playing, setPlaying] = useState(false)
  const [played, setPlayed] = useState(false)
  const [available, setAvailable] = useState(Boolean(audioBase64))
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const voiceRef = useRef<SpeechSynthesisVoice | null>(null)

  const stop = () => {
    audioRef.current?.pause()
    if (voiceRef.current) speechSynthesis.cancel()
    setPlaying(false)
  }

  const play = () => {
    const audio = audioRef.current
    if (audio) {
      audio.currentTime = 0
      // Browsers may block autoplay; the button then stays on "listen".
      audio.play().then(() => setPlayed(true), () => setPlaying(false))
    } else if (voiceRef.current) {
      speechSynthesis.cancel()
      const utterance = new SpeechSynthesisUtterance(fallbackText)
      utterance.voice = voiceRef.current
      utterance.lang = voiceRef.current.lang
      utterance.rate = 0.9
      utterance.onstart = () => {
        setPlaying(true)
        setPlayed(true)
      }
      utterance.onend = utterance.onerror = () => setPlaying(false)
      speechSynthesis.speak(utterance)
    }
  }

  useEffect(() => {
    let cancelled = false
    if (audioBase64) {
      const audio = new Audio(`data:audio/mpeg;base64,${audioBase64}`)
      audio.onplay = () => setPlaying(true)
      audio.onpause = audio.onended = () => setPlaying(false)
      audioRef.current = audio
      play()
    } else {
      void banglaVoice().then((voice) => {
        if (cancelled || !voice) return
        voiceRef.current = voice
        setAvailable(true)
        play()
      })
    }
    return () => {
      cancelled = true
      stop()
      audioRef.current = null
      voiceRef.current = null
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [audioBase64, fallbackText])

  if (!available) return null

  return (
    <button
      type="button"
      onClick={playing ? stop : play}
      className="flex min-h-16 w-full items-center justify-center gap-3 rounded-full bg-stamp px-5 text-xl font-bold text-white active:bg-stamp-deep"
    >
      {playing ? <StopIcon className="size-7" /> : <SpeakerIcon className="size-7" />}
      {playing ? t.result.stop : played ? t.result.replay : t.result.listen}
    </button>
  )
}

import { useEffect, useRef, useState, type PointerEvent } from 'react'
import { useI18n } from '../i18n'
import type { Translations } from '../i18n/translations'
import { MicIcon } from './icons'

export const MAX_RECORD_SECONDS = 120
// A press shorter than this is a tap: recording continues until the next tap.
const HOLD_MS = 500
const MIN_RECORD_MS = 1000
const MIME_TYPES = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4', 'audio/ogg']

type Phase = 'idle' | 'starting' | 'recording'
type MicProblem = keyof Translations['mic']

function clock(seconds: number, num: (n: number) => string): string {
  const pad = (n: number) => (n < 10 ? num(0) : '') + num(n)
  return `${num(Math.floor(seconds / 60))}:${pad(seconds % 60)}`
}

interface SpeakButtonProps {
  onRecorded: (audio: Blob) => void
  /** Replaces the line under the label while idle. */
  help?: string
}

export function SpeakButton({ onRecorded, help: idleHelp }: SpeakButtonProps) {
  const { t, num } = useI18n()
  const [phase, setPhaseState] = useState<Phase>('idle')
  const [seconds, setSeconds] = useState(0)
  const [problem, setProblem] = useState<MicProblem | null>(null)

  const phaseRef = useRef<Phase>('idle')
  const recorderRef = useRef<MediaRecorder | null>(null)
  const pressedAtRef = useRef(0)
  const discardRef = useRef(false)
  const onRecordedRef = useRef(onRecorded)
  onRecordedRef.current = onRecorded

  const setPhase = (next: Phase) => {
    phaseRef.current = next
    setPhaseState(next)
  }

  const finish = () => {
    if (recorderRef.current?.state === 'recording') recorderRef.current.stop()
  }

  // Leaving the screen mid-recording releases the microphone and sends nothing.
  useEffect(() => {
    discardRef.current = false
    return () => {
      discardRef.current = true
      finish()
    }
  }, [])

  const begin = async () => {
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === 'undefined') {
      setProblem('unsupported')
      return
    }
    setProblem(null)
    setPhase('starting')
    let stream: MediaStream
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    } catch {
      setPhase('idle')
      setProblem('denied')
      return
    }
    const release = () => stream.getTracks().forEach((track) => track.stop())
    if (discardRef.current) {
      release()
      return
    }

    const mimeType = MIME_TYPES.find((type) => MediaRecorder.isTypeSupported(type))
    // Speech stays clear at 32 kbps, and two minutes then fit in about 500 KB.
    const recorder = new MediaRecorder(stream, { mimeType, audioBitsPerSecond: 32_000 })
    const chunks: Blob[] = []
    const startedAt = Date.now()
    const tick = setInterval(() => {
      const elapsed = Math.floor((Date.now() - startedAt) / 1000)
      setSeconds(elapsed)
      if (elapsed >= MAX_RECORD_SECONDS) finish()
    }, 250)

    recorder.ondataavailable = (event) => {
      if (event.data.size > 0) chunks.push(event.data)
    }
    recorder.onstop = () => {
      clearInterval(tick)
      release()
      recorderRef.current = null
      if (discardRef.current) return
      setPhase('idle')
      setSeconds(0)
      if (Date.now() - startedAt < MIN_RECORD_MS) {
        setProblem('tooShort')
        return
      }
      onRecordedRef.current(new Blob(chunks, { type: recorder.mimeType || mimeType || 'audio/webm' }))
    }
    recorderRef.current = recorder
    recorder.start()
    setPhase('recording')
  }

  const press = () => {
    pressedAtRef.current = Date.now()
    if (phaseRef.current === 'idle') void begin()
    else if (phaseRef.current === 'recording') finish()
  }

  const onPointerDown = (event: PointerEvent<HTMLButtonElement>) => {
    // Keep receiving the release even if the finger slides off the button.
    event.currentTarget.setPointerCapture?.(event.pointerId)
    press()
  }

  const onPointerUp = () => {
    const held = Date.now() - pressedAtRef.current
    if (phaseRef.current === 'recording' && held >= HOLD_MS) finish()
  }

  const recording = phase === 'recording'
  const label = recording ? t.home.listening : phase === 'starting' ? t.home.micStarting : t.home.speak
  const help = recording
    ? `${clock(seconds, num)} / ${clock(MAX_RECORD_SECONDS, num)}`
    : (idleHelp ?? t.home.speakHelp)

  return (
    <div>
      <button
        type="button"
        aria-pressed={recording}
        onPointerDown={onPointerDown}
        onPointerUp={onPointerUp}
        onPointerCancel={onPointerUp}
        // Keyboard and switch access: pointer events do not fire, so a click toggles.
        onClick={(event) => event.detail === 0 && press()}
        onContextMenu={(event) => event.preventDefault()}
        className={`flex min-h-44 w-full touch-none flex-col items-center justify-center gap-2 rounded-[2rem] px-4 py-6 text-white select-none ${
          recording ? 'bg-stop' : 'bg-stamp active:bg-stamp-deep'
        }`}
      >
        <span
          className={`grid size-20 place-items-center rounded-full bg-white/15 ${recording ? 'animate-ring' : ''}`}
        >
          <MicIcon className="size-11" />
        </span>
        <span className="text-2xl font-bold">{label}</span>
        <span className={recording ? 'text-xl font-semibold tabular-nums' : 'text-base text-white/85'} role={recording ? 'timer' : undefined}>
          {help}
        </span>
      </button>
      {recording && <p className="mt-2 text-center text-base font-semibold">{t.home.listeningHelp}</p>}
      {problem && (
        <p role="alert" className="mt-3 rounded-2xl border-2 border-stop bg-stop-tint p-3 text-base font-semibold">
          {t.mic[problem]}
        </p>
      )}
    </div>
  )
}

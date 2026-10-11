import type { ReactNode, SVGProps } from 'react'

type IconProps = SVGProps<SVGSVGElement>

function Icon({ children, ...props }: IconProps & { children: ReactNode }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      {...props}
    >
      {children}
    </svg>
  )
}

export const MicIcon = (p: IconProps) => (
  <Icon {...p}>
    <rect x="9" y="3" width="6" height="11" rx="3" />
    <path d="M5 11a7 7 0 0 0 14 0M12 18v3" />
  </Icon>
)

export const CameraIcon = (p: IconProps) => (
  <Icon {...p}>
    <path d="M4 8h3l2-3h6l2 3h3v11H4z" />
    <circle cx="12" cy="13" r="3.5" />
  </Icon>
)

export const KeyboardIcon = (p: IconProps) => (
  <Icon {...p}>
    <rect x="3" y="6" width="18" height="12" rx="2" />
    <path d="M7 10h.01M11 10h.01M15 10h.01M8 14h8" />
  </Icon>
)

export const CrossIcon = (p: IconProps) => (
  <Icon strokeWidth={3.5} {...p}>
    <path d="M6 6l12 12M18 6L6 18" />
  </Icon>
)

export const ExclaimIcon = (p: IconProps) => (
  <Icon strokeWidth={3.5} {...p}>
    <path d="M12 4v10M12 19.5v.01" />
  </Icon>
)

export const CheckIcon = (p: IconProps) => (
  <Icon strokeWidth={3.5} {...p}>
    <path d="M5 12.5l4.5 4.5L19 7.5" />
  </Icon>
)

export const SpeakerIcon = (p: IconProps) => (
  <Icon {...p}>
    <path d="M4 10v4h3l5 4V6l-5 4zM16 9a4 4 0 0 1 0 6M18.5 6.5a8 8 0 0 1 0 11" />
  </Icon>
)

export const StopIcon = (p: IconProps) => (
  <Icon {...p}>
    <rect x="6" y="6" width="12" height="12" rx="2" fill="currentColor" />
  </Icon>
)

export const PhoneIcon = (p: IconProps) => (
  <Icon {...p}>
    <path d="M6 3h3l2 5-2.5 1.5a11 11 0 0 0 6 6L16 13l5 2v3a3 3 0 0 1-3 3A15 15 0 0 1 3 6a3 3 0 0 1 3-3z" />
  </Icon>
)

export const BackIcon = (p: IconProps) => (
  <Icon {...p}>
    <path d="M15 5l-7 7 7 7" />
  </Icon>
)

export const RetryIcon = (p: IconProps) => (
  <Icon {...p}>
    <path d="M4 12a8 8 0 1 0 2.5-5.8M4 4v5h5" />
  </Icon>
)

export const LockIcon = (p: IconProps) => (
  <Icon {...p}>
    <rect x="5" y="11" width="14" height="9" rx="2" />
    <path d="M8 11V8a4 4 0 0 1 8 0v3" />
  </Icon>
)

export const ChevronIcon = (p: IconProps) => (
  <Icon {...p}>
    <path d="M6 9l6 6 6-6" />
  </Icon>
)

export const ShieldLogo = (p: IconProps) => (
  <svg viewBox="0 0 40 44" aria-hidden="true" {...p}>
    <path d="M20 1l18 6.5V21c0 11.5-7.5 19.5-18 22C9.5 40.5 2 32.5 2 21V7.5z" fill="#27348b" />
    <circle cx="20" cy="12" r="4" fill="#ff6b5e" />
    <circle cx="20" cy="22" r="4" fill="#f5a300" />
    <circle cx="20" cy="32" r="4" fill="#4fd08a" />
  </svg>
)

import React from 'react'

type Props = {
  size?: number
  className?: string
}

export default function BusanFoodLogo({ size = 36, className = '' }: Props) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 100 100"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      style={{ verticalAlign: 'middle', cursor: 'pointer' }}
    >
      {/* Background circle badge */}
      <circle cx="50" cy="50" r="48" fill="#FFFDF8" stroke="#F47C3C" strokeWidth="4" />

      {/* Busan wave decoration accent (blue) */}
      <path
        d="M20 74 C 30 70, 40 78, 50 74 C 60 70, 70 78, 80 74 L 80 82 C 70 86, 60 78, 50 82 C 40 78, 30 86, 20 82 Z"
        fill="#1E5FA8"
        opacity="0.85"
      />

      {/* Traditional Food Bowl (Pork Soup / Stew Bowl) */}
      <path
        d="M24 45 C 24 66, 76 66, 76 45 Z"
        fill="#F47C3C"
      />
      {/* Bowl rim */}
      <ellipse cx="50" cy="45" rx="26" ry="6" fill="#FDE8D9" stroke="#F47C3C" strokeWidth="3" />

      {/* Bowl base */}
      <path d="M40 64 L 60 64 L 57 70 L 43 70 Z" fill="#BA5422" />

      {/* Delicious food garnish inside bowl */}
      <circle cx="44" cy="45" r="3" fill="#2A9A70" />
      <circle cx="50" cy="44" r="4" fill="#E65100" />
      <circle cx="56" cy="45" r="3" fill="#F6BE57" />

      {/* Rising steam lines */}
      <path
        d="M38 36 C 36 30, 42 26, 40 20"
        stroke="#F47C3C"
        strokeWidth="2.5"
        strokeLinecap="round"
        fill="none"
      />
      <path
        d="M50 34 C 48 27, 54 23, 52 16"
        stroke="#F47C3C"
        strokeWidth="3"
        strokeLinecap="round"
        fill="none"
      />
      <path
        d="M62 36 C 60 30, 66 26, 64 20"
        stroke="#F47C3C"
        strokeWidth="2.5"
        strokeLinecap="round"
        fill="none"
      />

      {/* Sparkle rating star accent */}
      <path
        d="M74 24 L76 28 L80 29 L77 32 L78 36 L74 34 L70 36 L71 32 L68 29 L72 28 Z"
        fill="#F6BE57"
      />
    </svg>
  )
}

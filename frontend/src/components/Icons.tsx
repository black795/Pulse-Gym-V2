const iconProps = {
  width: 20,
  height: 20,
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 2,
  strokeLinecap: 'round' as const,
  strokeLinejoin: 'round' as const,
  viewBox: '0 0 24 24',
};

export const IconGrid = (p: React.SVGProps<SVGSVGElement>) => (
  <svg {...iconProps} {...p}>
    <rect x="3" y="3" width="7" height="7" /><rect x="14" y="3" width="7" height="7" />
    <rect x="14" y="14" width="7" height="7" /><rect x="3" y="14" width="7" height="7" />
  </svg>
);

export const IconUsers = (p: React.SVGProps<SVGSVGElement>) => (
  <svg {...iconProps} {...p}>
    <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
    <circle cx="9" cy="7" r="4" />
    <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
    <path d="M16 3.13a4 4 0 0 1 0 7.75" />
  </svg>
);

export const IconCard = (p: React.SVGProps<SVGSVGElement>) => (
  <svg {...iconProps} {...p}>
    <rect x="1" y="4" width="22" height="16" rx="2" ry="2" />
    <line x1="1" y1="10" x2="23" y2="10" />
  </svg>
);

export const IconCheck = (p: React.SVGProps<SVGSVGElement>) => (
  <svg {...iconProps} {...p}>
    <polyline points="20 6 9 17 4 12" />
  </svg>
);

export const IconDumbbell = (p: React.SVGProps<SVGSVGElement>) => (
  <svg {...iconProps} {...p}>
    <path d="M6.5 6.5h11" /><path d="M6.5 17.5h11" />
    <path d="M3 9.5v5" /><path d="M21 9.5v5" />
    <path d="M1 8v8" /><path d="M23 8v8" />
    <path d="M3 12h18" />
  </svg>
);

export const IconList = (p: React.SVGProps<SVGSVGElement>) => (
  <svg {...iconProps} {...p}>
    <line x1="8" y1="6" x2="21" y2="6" /><line x1="8" y1="12" x2="21" y2="12" />
    <line x1="8" y1="18" x2="21" y2="18" />
    <line x1="3" y1="6" x2="3.01" y2="6" /><line x1="3" y1="12" x2="3.01" y2="12" />
    <line x1="3" y1="18" x2="3.01" y2="18" />
  </svg>
);

export const IconPulse = (p: React.SVGProps<SVGSVGElement>) => (
  <svg {...iconProps} {...p}>
    <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
  </svg>
);

export const IconShield = (p: React.SVGProps<SVGSVGElement>) => (
  <svg {...iconProps} {...p}>
    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
  </svg>
);

export const IconBanknote = (p: React.SVGProps<SVGSVGElement>) => (
  <svg {...iconProps} {...p}>
    <rect x="2" y="6" width="20" height="12" rx="2" />
    <circle cx="12" cy="12" r="2" />
    <path d="M6 12h.01M18 12h.01" />
  </svg>
);

export const IconFile = (p: React.SVGProps<SVGSVGElement>) => (
  <svg {...iconProps} {...p}>
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
    <polyline points="14 2 14 8 20 8" />
    <line x1="16" y1="13" x2="8" y2="13" />
    <line x1="16" y1="17" x2="8" y2="17" />
    <polyline points="10 9 9 9 8 9" />
  </svg>
);

export const IconBell = (p: React.SVGProps<SVGSVGElement>) => (
  <svg {...iconProps} {...p}>
    <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
    <path d="M13.73 21a2 2 0 0 1-3.46 0" />
  </svg>
);

export const IconSearch = (p: React.SVGProps<SVGSVGElement>) => (
  <svg {...iconProps} {...p}>
    <circle cx="11" cy="11" r="8" />
    <line x1="21" y1="21" x2="16.65" y2="16.65" />
  </svg>
);

export const IconChevronDown = (p: React.SVGProps<SVGSVGElement>) => (
  <svg {...iconProps} {...p}>
    <polyline points="6 9 12 15 18 9" />
  </svg>
);

export const IconChevronRight = (p: React.SVGProps<SVGSVGElement>) => (
  <svg {...iconProps} {...p}>
    <polyline points="9 18 15 12 9 6" />
  </svg>
);

export const IconPlus = (p: React.SVGProps<SVGSVGElement>) => (
  <svg {...iconProps} {...p}>
    <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
  </svg>
);

export const IconX = (p: React.SVGProps<SVGSVGElement>) => (
  <svg {...iconProps} {...p}>
    <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
  </svg>
);

export const IconAlertTriangle = (p: React.SVGProps<SVGSVGElement>) => (
  <svg {...iconProps} {...p}>
    <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
    <line x1="12" y1="9" x2="12" y2="13" />
    <line x1="12" y1="17" x2="12.01" y2="17" />
  </svg>
);

export const IconEdit = (p: React.SVGProps<SVGSVGElement>) => (
  <svg {...iconProps} {...p}>
    <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
    <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
  </svg>
);

export const IconEye = (p: React.SVGProps<SVGSVGElement>) => (
  <svg {...iconProps} {...p}>
    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
    <circle cx="12" cy="12" r="3" />
  </svg>
);

export const IconCalendar = (p: React.SVGProps<SVGSVGElement>) => (
  <svg {...iconProps} {...p}>
    <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
    <line x1="16" y1="2" x2="16" y2="6" /><line x1="8" y1="2" x2="8" y2="6" />
    <line x1="3" y1="10" x2="21" y2="10" />
  </svg>
);

export const IconTrendingUp = (p: React.SVGProps<SVGSVGElement>) => (
  <svg {...iconProps} {...p}>
    <polyline points="23 6 13.5 15.5 8.5 10.5 1 18" />
    <polyline points="17 6 23 6 23 12" />
  </svg>
);

export const IconCamera = (p: React.SVGProps<SVGSVGElement>) => (
  <svg {...iconProps} {...p}>
    <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z" />
    <circle cx="12" cy="13" r="4" />
  </svg>
);

export const IconMic = (p: React.SVGProps<SVGSVGElement>) => (
  <svg {...iconProps} {...p}>
    <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
    <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
    <line x1="12" y1="19" x2="12" y2="23" />
    <line x1="8" y1="23" x2="16" y2="23" />
  </svg>
);

export const IconSend = (p: React.SVGProps<SVGSVGElement>) => (
  <svg {...iconProps} {...p}>
    <line x1="22" y1="2" x2="11" y2="13" />
    <polygon points="22 2 15 22 11 13 2 9 22 2" />
  </svg>
);

export const IconHome = (p: React.SVGProps<SVGSVGElement>) => (
  <svg {...iconProps} {...p}>
    <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
    <polyline points="9 22 9 12 15 12 15 22" />
  </svg>
);

export const IconZap = (p: React.SVGProps<SVGSVGElement>) => (
  <svg {...iconProps} {...p}>
    <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
  </svg>
);

export const IconActivity = (p: React.SVGProps<SVGSVGElement>) => (
  <svg {...iconProps} {...p}>
    <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
  </svg>
);

export const IconUser = (p: React.SVGProps<SVGSVGElement>) => (
  <svg {...iconProps} {...p}>
    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
    <circle cx="12" cy="7" r="4" />
  </svg>
);

export const IconQR = (p: React.SVGProps<SVGSVGElement>) => (
  <svg {...iconProps} {...p}>
    <rect x="3" y="3" width="7" height="7" /><rect x="14" y="3" width="7" height="7" />
    <rect x="3" y="14" width="7" height="7" />
    <path d="M14 14h3v3h-3z" /><path d="M17 17h3v3h-3z" /><path d="M14 17h0" /><path d="M17 14h0" />
  </svg>
);

export const IconFlash = (p: React.SVGProps<SVGSVGElement>) => (
  <svg {...iconProps} {...p}>
    <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
  </svg>
);

export const IconImage = (p: React.SVGProps<SVGSVGElement>) => (
  <svg {...iconProps} {...p}>
    <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
    <circle cx="8.5" cy="8.5" r="1.5" />
    <polyline points="21 15 16 10 5 21" />
  </svg>
);

export const IconLogOut = (p: React.SVGProps<SVGSVGElement>) => (
  <svg {...iconProps} {...p}>
    <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
    <polyline points="16 17 21 12 16 7" /><line x1="21" y1="12" x2="9" y2="12" />
  </svg>
);

export const IconTrash = (p: React.SVGProps<SVGSVGElement>) => (
  <svg {...iconProps} {...p}>
    <polyline points="3 6 5 6 21 6" />
    <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
    <path d="M10 11v6M14 11v6M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2" />
  </svg>
);

export const IconLock = (p: React.SVGProps<SVGSVGElement>) => (
  <svg {...iconProps} {...p}>
    <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
    <path d="M7 11V7a5 5 0 0 1 10 0v4" />
  </svg>
);

export const IconArrowLeft = (p: React.SVGProps<SVGSVGElement>) => (
  <svg {...iconProps} {...p}>
    <line x1="19" y1="12" x2="5" y2="12" /><polyline points="12 19 5 12 12 5" />
  </svg>
);

export const IconBandage = (p: React.SVGProps<SVGSVGElement>) => (
  <svg {...iconProps} {...p}>
    <path d="M18 3l3 3-12 12-3-3z" transform="rotate(0)" />
    <path d="M5 16l-2 5 5-2" /><path d="M13 8l3 3" />
  </svg>
);

export const IconRefresh = (p: React.SVGProps<SVGSVGElement>) => (
  <svg {...iconProps} {...p}>
    <polyline points="23 4 23 10 17 10" /><polyline points="1 20 1 14 7 14" />
    <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
  </svg>
);

export const IconClock = (p: React.SVGProps<SVGSVGElement>) => (
  <svg {...iconProps} {...p}>
    <circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 16 14" />
  </svg>
);

export const IconMapPin = (p: React.SVGProps<SVGSVGElement>) => (
  <svg {...iconProps} {...p}>
    <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" /><circle cx="12" cy="10" r="3" />
  </svg>
);

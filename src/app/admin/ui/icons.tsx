/** The admin's icons: plain line drawings on a 24 grid, drawn in the text's own colour. No emoji anywhere. */
const P: Record<string, React.ReactNode> = {
  home: <path d="M3.5 10.5 12 3.5l8.5 7V20a1 1 0 0 1-1 1H15v-6.5H9V21H4.5a1 1 0 0 1-1-1z" />,
  orders: <><path d="M5.5 8h13l-1 12.5h-11z" /><path d="M9 8a3 3 0 0 1 6 0" /></>,
  people: <><circle cx="9" cy="8.5" r="3.5" /><path d="M2.5 20a6.5 6.5 0 0 1 13 0" /><path d="M15.5 5.2a3.5 3.5 0 0 1 0 6.6" /><path d="M18 14.3A6.5 6.5 0 0 1 21.5 20" /></>,
  shirt: <path d="M8.5 3.5 3 6.5l2 4.5 2.5-1V20.5h9V10l2.5 1 2-4.5-5.5-3a3.5 3.5 0 0 1-7 0z" />,
  visitors: <><path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12z" /><circle cx="12" cy="12" r="3" /></>,
  settings: <><path d="M4 6.5h9M17 6.5h3M4 12h3M11 12h9M4 17.5h11M19 17.5h1" /><circle cx="15" cy="6.5" r="2" /><circle cx="9" cy="12" r="2" /><circle cx="17" cy="17.5" r="2" /></>,
  chevron: <path d="m9.5 6 6 6-6 6" />,
  back: <path d="m14.5 6-6 6 6 6" />,
  down: <path d="m6 9.5 6 6 6-6" />,
  out: <><path d="M8 16 16 8" /><path d="M9 8h7v7" /></>,
  up: <><path d="m4 16 5.5-5.5 4 4L20 8" /><path d="M14.5 8H20v5.5" /></>,
  fall: <><path d="m4 8 5.5 5.5 4-4L20 16" /><path d="M14.5 16H20v-5.5" /></>,
  check: <path d="m5 12.5 4.5 4.5L19 7.5" />,
  x: <path d="M6.5 6.5l11 11M17.5 6.5l-11 11" />,
  alert: <><path d="M12 4 2.8 19.5h18.4z" /><path d="M12 10v4.5" /><path d="M12 17.2v.1" /></>,
  search: <><circle cx="11" cy="11" r="6.5" /><path d="m20 20-4.2-4.2" /></>,
  mail: <><rect x="3" y="5.5" width="18" height="13" rx="2" /><path d="m3.5 7 8.5 6 8.5-6" /></>,
  truck: <><path d="M2.5 6.5h11.5v9.5H2.5z" /><path d="M14 10h4l3 3.2V16h-7" /><circle cx="6.5" cy="17.5" r="1.8" /><circle cx="17" cy="17.5" r="1.8" /></>,
  print: <><path d="M7 9V3.5h10V9" /><rect x="3" y="9" width="18" height="8" rx="2" /><path d="M7 14h10v6.5H7z" /></>,
  refresh: <><path d="M19.5 11A7.5 7.5 0 0 0 5.6 7.2M4.5 4v3.8h3.8" /><path d="M4.5 13a7.5 7.5 0 0 0 13.9 3.8m1.1 3.2v-3.8h-3.8" /></>,
  trash: <><path d="M4 7h16M10 11v6M14 11v6" /><path d="M6 7l1 13h10l1-13M9 7V4h6v3" /></>,
  edit: <path d="M4 20h4L19.5 8.5l-4-4L4 16z" />,
  signout: <><path d="M14.5 4H19v16h-4.5" /><path d="m10 8-4 4 4 4M6 12h10" /></>,
  live: <path d="M3 12h4l2.5-6.5 5 13L17 12h4" />,
  globe: <><circle cx="12" cy="12" r="8.5" /><path d="M3.5 12h17M12 3.5c2.5 2.6 3.5 5.4 3.5 8.5s-1 5.9-3.5 8.5c-2.5-2.6-3.5-5.4-3.5-8.5s1-5.9 3.5-8.5z" /></>,
  phone: <><rect x="7" y="2.5" width="10" height="19" rx="2.5" /><path d="M11 18.2h2" /></>,
  desktop: <><rect x="3" y="4" width="18" height="12" rx="2" /><path d="M9 20h6M12 16v4" /></>,
  clock: <><circle cx="12" cy="12" r="8.5" /><path d="M12 7.5V12l3 2" /></>,
  card: <><rect x="2.5" y="5.5" width="19" height="13" rx="2" /><path d="M2.5 10h19" /></>,
  download: <><path d="M12 4v11M7 10l5 5 5-5" /><path d="M5 20h14" /></>,
  note: <><path d="M5 4h14v11l-5 5H5z" /><path d="M14 20v-5h5" /></>,
  shield: <path d="M12 3.5 5 6.2v5.6c0 4.4 3 7.6 7 8.7 4-1.1 7-4.3 7-8.7V6.2z" />,
  shop: <><path d="M4.5 9 5.7 4h12.6l1.2 5" /><path d="M4.5 9v11h15V9z" /><path d="M9.5 20v-5.5h5V20" /></>,
  list: <path d="M8.5 6.5H20M8.5 12H20M8.5 17.5H20M4 6.5h.5M4 12h.5M4 17.5h.5" />,
  key: <><circle cx="8" cy="15" r="4" /><path d="m11 12 8.5-8.5M16.5 6.5l2.5 2.5" /></>,
  user: <><circle cx="12" cy="8.5" r="4" /><path d="M4.5 20.5a7.5 7.5 0 0 1 15 0" /></>,
  pin: <><path d="M12 21s6.5-5.6 6.5-11.5a6.5 6.5 0 0 0-13 0C5.5 15.4 12 21 12 21z" /><circle cx="12" cy="9.5" r="2.3" /></>,
  link: <><path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1" /><path d="M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1" /></>,
  filter: <path d="M4 5.5h16l-6.2 7.5v5.5l-3.6-1.8V13z" />,
  plus: <path d="M12 5v14M5 12h14" />,
  bag: <><path d="M5 8.5h14l-1 12H6z" /><path d="M9 8.5V7a3 3 0 0 1 6 0v1.5" /></>,
  money: <><rect x="2.5" y="6" width="19" height="12" rx="2" /><circle cx="12" cy="12" r="2.6" /><path d="M6 9.5v.1M18 14.4v.1" /></>,
  chart: <path d="M4 20V10M10 20V4M16 20v-7M22 20H2" />,
  bot: <><rect x="5" y="8" width="14" height="11" rx="3" /><path d="M12 4v4M9.5 13v.1M14.5 13v.1" /></>,
  return: <><path d="M9 5 4.5 9.5 9 14" /><path d="M4.5 9.5H15a5 5 0 0 1 0 10h-3" /></>,
  eye: <><path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12z" /><circle cx="12" cy="12" r="3" /></>,
  eyeOff: <><path d="M10.6 5.1A9.8 9.8 0 0 1 12 5c6.4 0 10 7 10 7a17 17 0 0 1-2.7 3.6M6.6 6.6C3.7 8.4 2 12 2 12s3.6 7 10 7a9.6 9.6 0 0 0 5.4-1.6" /><path d="M9.9 9.9a3 3 0 0 0 4.2 4.2M3.5 3.5l17 17" /></>,
  dot: <circle cx="12" cy="12" r="3" fill="currentColor" stroke="none" />,
};

export type IconName = keyof typeof P;

export function Icon({ name, className = "h-5 w-5" }: { name: IconName; className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round" aria-hidden className={`shrink-0 ${className}`}>
      {P[name]}
    </svg>
  );
}

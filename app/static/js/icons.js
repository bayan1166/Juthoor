const PATHS = {
  tree: 'M12 21v-7M12 14c-4 0-7-3-7-7 4 0 7 3 7 7zM12 14c4 0 7-3 7-7-4 0-7 3-7 7zM8 21h8',
  pencil: 'M4 20l4-1 11-11a2.1 2.1 0 00-3-3L5 16l-1 4zM14 7l3 3',
  spark: 'M12 3l1.8 4.7L18.5 9l-4.7 1.8L12 15.5l-1.8-4.7L5.5 9l4.7-1.3L12 3zM18 15l.8 2.2L21 18l-2.2.8L18 21l-.8-2.2L15 18l2.2-.8L18 15z',
  users: 'M16 20v-1.5a3.5 3.5 0 00-3.5-3.5h-5A3.5 3.5 0 004 18.5V20M10 11a3.5 3.5 0 100-7 3.5 3.5 0 000 7zM20 20v-1.5a3.5 3.5 0 00-2.6-3.4M15.5 4.2a3.5 3.5 0 010 6.6',
  chat: 'M4 5h16v11H9l-5 4V5z',
  card: 'M3 6h18v12H3zM3 10h18M7 15h4',
  chart: 'M4 20V4M4 20h16M8 16v-5M12 16V8M16 16v-3',
  logout: 'M10 4H5v16h5M15 8l4 4-4 4M19 12H9',
  sun: 'M12 16a4 4 0 100-8 4 4 0 000 8zM12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4',
  moon: 'M20 14.5A8 8 0 019.5 4 8 8 0 1020 14.5z',
  lock: 'M6 11h12v9H6zM8 11V8a4 4 0 018 0v3',
  check: 'M5 12.5l4.5 4.5L19 7.5',
  checks: 'M2 13l4 4L14 8M10 15l2 2L21 8',
  x: 'M6 6l12 12M18 6L6 18',
  send: 'M21 3L3 10l7 3 3 7 8-17z',
  plus: 'M12 5v14M5 12h14',
  trash: 'M5 7h14M10 7V4h4v3M7 7l1 13h8l1-13',
  download: 'M12 4v11M7 11l5 5 5-5M5 20h14',
  upload: 'M12 16V5M7 9l5-5 5 5M5 20h14',
  trophy: 'M8 4h8v5a4 4 0 01-8 0V4zM8 6H5v1a3 3 0 003 3M16 6h3v1a3 3 0 01-3 3M12 13v4M9 20h6',
  clock: 'M12 21a9 9 0 100-18 9 9 0 000 18zM12 7v5l3 2',
  copy: 'M9 9h10v11H9zM5 15V4h10',
  eye: 'M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12zM12 15a3 3 0 100-6 3 3 0 000 6z',
  eyeoff: 'M3 3l18 18M10.6 6.2A9.6 9.6 0 0112 5c6 0 10 7 10 7a17 17 0 01-3.2 4M6.2 6.9A17 17 0 002 12s4 7 10 7a9.6 9.6 0 004-.9',
  chevl: 'M14 5l-7 7 7 7',
  chevr: 'M10 5l7 7-7 7',
  book: 'M5 4h10a3 3 0 013 3v13H8a3 3 0 01-3-3V4zM5 17a3 3 0 013-3h10',
  flag: 'M5 21V4M5 4h11l-2 4 2 4H5',
  bolt: 'M13 3L5 14h6l-1 7 8-11h-6l1-7z',
  shield: 'M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6l8-3zM9 12l2 2 4-4',
  file: 'M7 3h7l4 4v14H7zM14 3v4h4',
  search: 'M11 18a7 7 0 100-14 7 7 0 000 14zM16 16l5 5',
  star: 'M12 3l2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1L3.2 9.5l6.1-.9L12 3z',
  target: 'M12 21a9 9 0 100-18 9 9 0 000 18zM12 16a4 4 0 100-8 4 4 0 000 8z',
  user: 'M12 12a4 4 0 100-8 4 4 0 000 8zM4 21a8 8 0 0116 0',
  print: 'M7 9V4h10v5M7 17H5v-6h14v6h-2M7 14h10v6H7z',
  refresh: 'M20 11a8 8 0 10-2.3 5.7M20 4v7h-7',
  edit: 'M4 20h4L19 9a2.1 2.1 0 00-3-3L5 17v3z',
  info: 'M12 21a9 9 0 100-18 9 9 0 000 18zM12 11v5M12 8v.01',
  alert: 'M12 3l10 18H2L12 3zM12 10v5M12 18v.01',
  home: 'M4 11l8-7 8 7v9h-5v-6H9v6H4v-9z',
  menu: 'M4 7h16M4 12h16M4 17h16',
};

export function iconSvg(name) {
  const d = PATHS[name] || PATHS.info;
  return `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="${d}"/></svg>`;
}

let logoCounter = 0;

export function logoMark(cls = 'brand-mark') {
  logoCounter += 1;
  const id = `lg${logoCounter}`;
  return `<svg class="${cls}" viewBox="0 0 48 48" role="img" aria-label="جذور"><defs><linearGradient id="${id}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#0C4A33"/><stop offset="1" stop-color="#17B374"/></linearGradient></defs><rect width="48" height="48" rx="13" fill="url(#${id})"/><path d="M27 11v17.5c0 5-3.6 8.5-9 8.5" fill="none" stroke="#F4FBF6" stroke-width="4.6" stroke-linecap="round"/><path d="M27 21.5c0-6.5 4.6-10.5 11-10.5 0 6.6-4.4 10.8-11 10.5z" fill="#C6F36B"/><circle cx="18" cy="37" r="2.4" fill="#C6F36B"/></svg>`;
}

export function brandHtml() {
  return `${logoMark()}<span class="brand-word"><b>جذور</b><i>JUTHOOR</i></span>`;
}

export function leafAvatarSvg() {
  return `<svg viewBox="0 0 48 48" aria-hidden="true"><rect width="48" height="48" rx="24" fill="#E3F8EC"/><path d="M24 36V22" stroke="#12684A" stroke-width="3" stroke-linecap="round" fill="none"/><path d="M24 24c0-7 5-11 12-11 0 7-5 11-12 11zM24 28c0-5-4-8-10-8 0 5 4 8 10 8z" fill="#16A36B"/></svg>`;
}

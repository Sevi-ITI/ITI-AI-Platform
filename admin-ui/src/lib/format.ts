// Display formats for the console. The API sends UTC; people read Asia/Manila time.

const MANILA = "Asia/Manila";
const LOCALE = "en-PH";

const timeFormat = new Intl.DateTimeFormat(LOCALE, {
  timeZone: MANILA,
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
  hourCycle: "h23",
});

const dateTimeFormat = new Intl.DateTimeFormat(LOCALE, {
  timeZone: MANILA,
  month: "short",
  day: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
});

const stampFormat = new Intl.DateTimeFormat(LOCALE, {
  timeZone: MANILA,
  month: "short",
  day: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
  hourCycle: "h23",
});

const countFormat = new Intl.NumberFormat(LOCALE);

export function formatTime(value: string | Date): string {
  return timeFormat.format(new Date(value));
}

export function formatDateTime(value: string | Date): string {
  return dateTimeFormat.format(new Date(value));
}

/** Log timestamps, to the second: "Oct 8, 14:01:02". */
export function formatStamp(value: string | Date): string {
  return stampFormat.format(new Date(value));
}

export function formatCount(value: number): string {
  return countFormat.format(value);
}

/** 840 → "840 ms", 3120 → "3.1 s"; null → "–" (no data). */
export function formatMs(ms: number | null): string {
  if (ms === null) {
    return "–";
  }
  return ms < 1000 ? `${Math.round(ms)} ms` : `${(ms / 1000).toFixed(1)} s`;
}

/** part / whole as "91%"; "–" when there is nothing to divide by. */
export function formatPercent(part: number, whole: number): string {
  return whole === 0 ? "–" : `${Math.round((part / whole) * 100)}%`;
}

/** 3072 → "3.0 GB", 600 → "600 MB". */
export function formatMb(mb: number): string {
  return mb < 1024 ? `${Math.round(mb)} MB` : `${(mb / 1024).toFixed(1)} GB`;
}

/** Uptime: 4000 → "1 h 6 min", 200000 → "2 d 7 h". */
export function formatUptime(seconds: number): string {
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);
  if (days > 0) {
    return `${days} d ${hours % 24} h`;
  }
  if (hours > 0) {
    return `${hours} h ${minutes % 60} min`;
  }
  return `${minutes} min`;
}

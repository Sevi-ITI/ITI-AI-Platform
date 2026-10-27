// Philippine time (Asia/Manila, UTC+8) for the clock tower, the sun and the auto theme (V2). Super admin extras,
// kept in cookies so the server renders the right theme on the first paint:
//   iti_game_pht_auto = "on": the theme follows the time (light from 05:48 to 18:00, dark otherwise)
//   iti_game_pht_sim  = minutes after midnight (0–1439): a simulated time; a browser-session cookie

import type { Theme } from "@/hq/theme";

export const PHT_AUTO_COOKIE = "iti_game_pht_auto";
export const PHT_SIM_COOKIE = "iti_game_pht_sim";

const SUNRISE = 5.8; // ~05:48 in Manila
const SUNSET = 18.0;

export type Pht = {
  hours: number; // 0–23
  minutes: number;
  seconds: number;
  fractionalHour: number; // 15.5 = 3:30 PM
  isDaylight: boolean;
  phase: string; // "Morning", "Night"…
  elevation: number; // the sun's height in degrees, -78 (midnight) to 78 (noon)
  simulated: boolean;
  date: string; // "Tue, Oct 27, 2026" (the real date, also when the time is simulated)
};

export function simFrom(value: string | undefined): number | null {
  const minutes = Number(value);
  return value !== undefined && value !== "" && Number.isInteger(minutes) && minutes >= 0 && minutes < 1440
    ? minutes
    : null;
}

export function autoFrom(value: string | undefined): boolean {
  return value === "on";
}

const FORMAT = new Intl.DateTimeFormat("en-US", {
  timeZone: "Asia/Manila",
  weekday: "short",
  year: "numeric",
  month: "short",
  day: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
  hourCycle: "h23",
});

function phaseOf(h: number): string {
  if (h >= 5.5 && h < 7) return "Dawn";
  if (h >= 7 && h < 11) return "Morning";
  if (h >= 11 && h < 15) return "Midday";
  if (h >= 15 && h < 17.3) return "Afternoon";
  if (h >= 17.3 && h < 18.5) return "Sunset";
  return "Night";
}

/** The time in Manila now, or the simulated time (its seconds still tick with the real clock). */
export function phtNow(simMinutes: number | null, now = new Date()): Pht {
  const parts = Object.fromEntries(FORMAT.formatToParts(now).map((p) => [p.type, p.value]));
  const seconds = Number(parts.second);
  const hours = simMinutes === null ? Number(parts.hour) : Math.floor(simMinutes / 60);
  const minutes = simMinutes === null ? Number(parts.minute) : simMinutes % 60;
  const fractionalHour = hours + minutes / 60 + seconds / 3600;
  return {
    hours,
    minutes,
    seconds,
    fractionalHour,
    isDaylight: fractionalHour >= SUNRISE && fractionalHour < SUNSET,
    phase: phaseOf(fractionalHour),
    elevation: Math.round(Math.sin(((fractionalHour - 6) / 12) * Math.PI) * 78),
    simulated: simMinutes !== null,
    date: `${parts.weekday}, ${parts.month} ${parts.day}, ${parts.year}`,
  };
}

/** "3:08:12 PM" */
export function clockText(pht: Pht, withSeconds = true): string {
  const h12 = pht.hours % 12 === 0 ? 12 : pht.hours % 12;
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${h12}:${pad(pht.minutes)}${withSeconds ? `:${pad(pht.seconds)}` : ""} ${pht.hours < 12 ? "AM" : "PM"}`;
}

export function themeForPht(pht: Pht): Theme {
  return pht.isDaylight ? "light" : "dark";
}

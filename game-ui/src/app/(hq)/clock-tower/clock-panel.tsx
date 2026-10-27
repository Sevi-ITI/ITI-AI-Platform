"use client";

import { useState, useSyncExternalStore, useTransition } from "react";

import { clockText, type Pht, phtNow, themeForPht } from "@/hq/pht";

import { setPhtAuto, setPhtSim } from "./actions";
import styles from "./clock.module.css";

const PRESETS: { minutes: number; label: string }[] = [
  { minutes: 7 * 60 + 24, label: "7:24 AM · morning" },
  { minutes: 12 * 60, label: "12:00 PM · noon" },
  { minutes: 17 * 60 + 30, label: "5:30 PM · sunset" },
  { minutes: 21 * 60, label: "9:00 PM · night" },
];

// A clock that ticks once a second in the browser; null on the server (no time mismatch when the page hydrates).
function subscribe(tick: () => void) {
  const timer = window.setInterval(tick, 1000);
  return () => window.clearInterval(timer);
}
const nowSecond = () => Math.floor(Date.now() / 1000);
const noSecond = () => null;

function minutesText(minutes: number): string {
  return clockText(phtNow(minutes, new Date(0)), false);
}

function AnalogClock({ pht }: { pht: Pht }) {
  const hour = (((pht.hours % 12) + pht.minutes / 60) / 12) * 360;
  const minute = ((pht.minutes + pht.seconds / 60) / 60) * 360;
  const second = (pht.seconds / 60) * 360;
  return (
    <svg viewBox="0 0 200 200" className={styles.analog} role="img" aria-label={`Clock showing ${clockText(pht, false)}`}>
      <circle cx="100" cy="100" r="92" className={styles.face} />
      {Array.from({ length: 60 }, (_, i) => (
        <line
          key={i}
          x1="100"
          y1={i % 5 === 0 ? 14 : 17}
          x2="100"
          y2={i % 5 === 0 ? 25 : 21}
          className={i % 5 === 0 ? styles.tickMajor : styles.tick}
          transform={`rotate(${i * 6} 100 100)`}
        />
      ))}
      {Array.from({ length: 12 }, (_, i) => {
        const angle = ((i + 1) / 12) * Math.PI * 2;
        return (
          <text key={i} x={100 + Math.sin(angle) * 64} y={104 - Math.cos(angle) * 64} className={styles.numeral}>
            {i + 1}
          </text>
        );
      })}
      <line x1="100" y1="100" x2="100" y2="56" className={styles.hourHand} transform={`rotate(${hour} 100 100)`} />
      <line x1="100" y1="100" x2="100" y2="34" className={styles.minuteHand} transform={`rotate(${minute} 100 100)`} />
      <line x1="100" y1="112" x2="100" y2="28" className={styles.secondHand} transform={`rotate(${second} 100 100)`} />
      <circle cx="100" cy="100" r="4" className={styles.pin} />
    </svg>
  );
}

// The clock tower's page: Manila time (analog + digital), the sun, and the super admin's controls: the theme that
// follows the time, and a simulated time (slider and presets) for trying the light at any hour.
export default function ClockPanel({ auto, sim }: { auto: boolean; sim: number | null }) {
  const second = useSyncExternalStore(subscribe, nowSecond, noSecond);
  const pht = second === null ? null : phtNow(sim, new Date(second * 1000));
  const [draft, setDraft] = useState<number | null>(null); // the slider while it is being moved
  const [pending, startTransition] = useTransition();

  const commitSim = (minutes: number | null) => {
    startTransition(async () => {
      await setPhtSim(minutes);
      setDraft(null);
    });
  };

  const sliderValue = draft ?? sim ?? (pht ? pht.hours * 60 + pht.minutes : 0);

  return (
    <div className={styles.room}>
      <section className={styles.card} aria-labelledby="clock-now">
        <h2 id="clock-now">Philippine time</h2>
        <div className={styles.now}>
          {pht ? <AnalogClock pht={pht} /> : <div className={styles.analog} aria-hidden="true" />}
          <div className={styles.digital}>
            <p className={styles.time}>{pht ? clockText(pht) : "…"}</p>
            <p className={styles.muted}>{pht?.date ?? " "} · Asia/Manila (UTC+8)</p>
            {sim === null ? (
              <p className={styles.live}>● Live time</p>
            ) : (
              <p className={styles.simulated} role="status">
                ⚠ Simulated time: not the real time
              </p>
            )}
            {pht && (
              <p>
                {pht.phase} · the sun is {Math.abs(pht.elevation)}° {pht.elevation >= 0 ? "above" : "below"} the horizon
              </p>
            )}
          </div>
        </div>
      </section>

      <section className={styles.card} aria-labelledby="clock-theme">
        <h2 id="clock-theme">Theme by the time of day</h2>
        <label className={styles.check}>
          <input
            type="checkbox"
            checked={auto}
            disabled={pending}
            onChange={(e) => {
              const on = e.target.checked;
              startTransition(() => setPhtAuto(on));
            }}
          />
          Light from 5:48 AM to 6:00 PM, dark otherwise
        </label>
        <p className={styles.muted}>
          {auto && pht
            ? `On: ${themeForPht(pht)} now. The sun / moon button turns it off.`
            : "Off: the sun / moon button decides."}
        </p>
      </section>

      <section className={styles.card} aria-labelledby="clock-sim">
        <h2 id="clock-sim">Simulated time</h2>
        <p className={styles.muted}>
          Moves the tower&apos;s hands, the sun and (when the theme follows the time) the theme. Only in this browser,
          until it closes.
        </p>
        <label className={styles.slider}>
          <span>
            Time of day: <strong>{minutesText(sliderValue)}</strong>
          </span>
          <input
            type="range"
            min={0}
            max={1439}
            step={1}
            value={sliderValue}
            disabled={pending}
            onChange={(e) => setDraft(Number(e.target.value))}
            onPointerUp={() => draft !== null && commitSim(draft)}
            onKeyUp={() => draft !== null && commitSim(draft)}
          />
        </label>
        <div className={styles.buttons}>
          {PRESETS.map((p) => (
            <button
              key={p.minutes}
              type="button"
              className={styles.button}
              aria-pressed={sim === p.minutes}
              disabled={pending}
              onClick={() => commitSim(p.minutes)}
            >
              {p.label}
            </button>
          ))}
          <button
            type="button"
            className={`${styles.button} ${styles.primary}`}
            disabled={pending || sim === null}
            onClick={() => commitSim(null)}
          >
            Back to live time
          </button>
        </div>
      </section>
    </div>
  );
}

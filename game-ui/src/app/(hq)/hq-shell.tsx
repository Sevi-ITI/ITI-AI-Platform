"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { initials } from "@/lib/format";
import { logOut } from "@/lib/session/actions";
import { canEnter, canEnterWing, type Role, type Station, STATIONS, stationForPath, WINGS } from "@/hq/stations";
import type { CityBlock } from "@/hq/scene/city";
import type { RoomProps } from "@/hq/scene/props";
import type { Theme } from "@/hq/theme";
import type { View } from "@/hq/view";

import type { SceneControls, WallMode } from "./hq-scene";
import styles from "./hq.module.css";
import {
  AccountsIcon,
  ChatIcon,
  CompaniesIcon,
  DocumentsIcon,
  KeysIcon,
  LogOutIcon,
  MenuIcon,
  MoonIcon,
  OverviewIcon,
  PerformanceIcon,
  RequestLogIcon,
  StatusErrorIcon,
  StatusOkIcon,
  StatusWarnIcon,
  SunIcon,
  ToolsIcon,
  UsageIcon,
  UsersIcon,
} from "./kit/icons";
import Toaster from "./kit/toast";
import { toggleTheme } from "./theme-actions";
import { useAutoTheme } from "./use-auto-theme";
import { useHealth } from "./use-health";
import { setView } from "./view-actions";

// three.js only runs in the browser, and only when the 3D view is on: the list view never downloads it.
const HqScene = dynamic(() => import("./hq-scene"), {
  ssr: false,
  loading: () => <p className={styles.loading}>Opening the HQ…</p>,
});

// The list view's room icons (the same icons as admin-ui's sidebar)
const ROOM_ICONS: Record<string, () => React.ReactElement> = {
  overview: OverviewIcon,
  performance: PerformanceIcon,
  requests: RequestLogIcon,
  documents: DocumentsIcon,
  chat: ChatIcon,
  companies: CompaniesIcon,
  apps: KeysIcon,
  users: UsersIcon,
  usage: UsageIcon,
  accounts: AccountsIcon,
  tools: ToolsIcon,
};

const WALL_LABELS: Record<WallMode, string> = { auto: "Walls: auto", down: "Walls: down", up: "Walls: up" };
const NEXT_WALLS: Record<WallMode, WallMode> = { auto: "down", down: "up", up: "auto" };

type Props = {
  name: string;
  role: Role;
  view: View;
  theme: Theme;
  phtAuto: boolean; // the theme follows Manila's time of day (clock tower, V2)
  phtSim: number | null; // a simulated time of day in minutes (clock tower), null = live
  city: CityBlock[]; // V4: the app city blocks (real apps and their linked companies; super admins' 3D view only)
  roomProps: RoomProps; // the rooms' live props (collections, companies, MCP connections, tools; 3D view only)
  children: React.ReactNode;
};

// Everything around a page: the 3D HQ with its floating HUD (top bar, wings dock, camera bar, the page in a panel
// on the right) or the plain list view (a sidebar of rooms and the page). The URL decides which room is open.
export default function HqShell({ name, role, view, theme, phtAuto, phtSim, city, roomProps, children }: Props) {
  const pathname = usePathname();
  const router = useRouter();
  const station = stationForPath(pathname);

  const [noWebgl, setNoWebgl] = useState(false);
  const [dockOpen, setDockOpen] = useState(false);
  const [barOpen, setBarOpen] = useState(false);
  const [panelOpen, setPanelOpen] = useState(true);
  const [shownPath, setShownPath] = useState(pathname);
  const [walls, setWalls] = useState<WallMode>("auto");
  const [notice, setNotice] = useState<string | null>(null);
  const controls = useRef<SceneControls | null>(null);
  const noticeTimer = useRef<number | undefined>(undefined);
  const hqRef = useRef<HTMLDivElement>(null);
  const topBarRef = useRef<HTMLDivElement>(null);
  const health = useHealth();
  useAutoTheme(phtAuto, phtSim, theme);

  // Any room change (a click, a link, back / forward) shows the panel again. Set while rendering, React's way of
  // adjusting state to a new prop, so there is no extra render with the old panel state.
  if (shownPath !== pathname) {
    setShownPath(pathname);
    setPanelOpen(true);
  }
  const in3d = view === "3d" && !noWebgl;

  // The top bar wraps to two rows in a narrow window: keep the dock and the panel below wherever it ends.
  useEffect(() => {
    const hq = hqRef.current;
    const bar = topBarRef.current;
    if (!hq || !bar) return;
    const observer = new ResizeObserver(() => hq.style.setProperty("--hud-bottom", `${bar.offsetTop + bar.offsetHeight}px`));
    observer.observe(bar);
    return () => observer.disconnect();
  }, [in3d]);

  const tell = (message: string) => {
    setNotice(message);
    window.clearTimeout(noticeTimer.current);
    noticeTimer.current = window.setTimeout(() => setNotice(null), 4000);
  };

  const header = (
    <header className={styles.panelHeader}>
      <p className={styles.breadcrumbs}>
        ITI AI HQ › {WINGS.find((w) => w.id === station?.wing)?.title ?? "Lobby"} ›{" "}
        <span translate="no">{station?.route ?? pathname}</span>
      </p>
      <h1 className={styles.panelTitle} id="room-title" tabIndex={-1}>
        {station?.title ?? "ITI AI HQ"}
      </h1>
      {station && (
        <p className={styles.panelDesc}>
          {station.roomObject}: {station.desc}
        </p>
      )}
    </header>
  );

  const body =
    station && !canEnter(station, role) ? (
      <p role="alert" className={styles.locked}>
        🔒 This room is locked for your role ({role.replace("_", " ")}).
      </p>
    ) : (
      children
    );

  const accountBar = (
    <div className={`${styles.card} ${styles.accountBar}`}>
      <span className={styles.who}>
        {name} <span className={styles.role}>{role.replace("_", " ")}</span>
      </span>
      {role === "super_admin" && (
        <form action={setView.bind(null, in3d ? "list" : "3d")}>
          <button type="submit" className={styles.button}>
            {in3d ? "☰ List view" : "◧ 3D HQ"}
          </button>
        </form>
      )}
      <form action={toggleTheme}>
        <button
          type="submit"
          className={`${styles.button} ${styles.iconButton}`}
          aria-label={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
          title={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
        >
          {theme === "dark" ? <SunIcon /> : <MoonIcon />}
        </button>
      </form>
      <form action={logOut}>
        <button type="submit" className={styles.button}>
          Log out
        </button>
      </form>
    </div>
  );

  const brand = (
    <div className={`${styles.card} ${styles.brand}`}>
      <span className={styles.brandMark} aria-hidden="true">
        ITI
      </span>
      <span className={styles.brandText}>
        <strong>ITI AI HQ</strong>
        <span>Intellismart Technology Inc.</span>
      </span>
    </div>
  );

  // The system's health in words + a shape (check, triangle, cross); the roof beacon repeats it in 3D. A click opens
  // Overview (not for testers: they can't open it).
  const HealthIcon = health?.tone === "ok" ? StatusOkIcon : health?.tone === "warn" ? StatusWarnIcon : StatusErrorIcon;
  const healthContent = (
    <>
      {health ? <HealthIcon /> : <span className={styles.healthChecking} aria-hidden="true" />}
      {health ? health.text : "Checking…"}
    </>
  );
  const healthClass = `${styles.card} ${styles.healthPill} ${health ? styles[`health_${health.tone}`] : ""}`;
  const healthTitle = health ? `${health.text}\n${health.detail}` : "Checking the system…";
  const healthPill =
    role === "tester" ? (
      <span className={healthClass} title={healthTitle} role="status">
        {healthContent}
      </span>
    ) : (
      <Link href="/" className={healthClass} title={healthTitle}>
        {healthContent}
      </Link>
    );

  const noticeLine = (
    <p className={styles.notice} role="status" aria-live="polite" data-shown={notice ? "" : undefined}>
      {notice}
    </p>
  );

  // The list view fills the window: the sidebar always shows every room, and only the page itself scrolls (and only
  // when it is longer than the window). On a phone the rooms fold into a menu (a native popover: Esc and a click
  // outside close it, as in admin-ui).
  if (!in3d) {
    const themeLabel = theme === "dark" ? "Switch to light theme" : "Switch to dark theme";
    return (
      <div className={styles.listShell}>
        <a href="#room-title" className={styles.skip}>
          Skip to the page
        </a>
        <aside className={styles.sidebar}>
          <div className={styles.sideTop}>
            {brand}
            <button
              type="button"
              className={`${styles.button} ${styles.menuButton}`}
              popoverTarget="room-nav"
              aria-label="Rooms"
            >
              <MenuIcon />
            </button>
          </div>
          {healthPill}
          {noWebgl && <p className={styles.locked}>This browser can&apos;t show the 3D HQ, so here is the list.</p>}
          <nav id="room-nav" popover="auto" aria-label="Rooms" className={styles.sideNav}>
            {WINGS.filter((w) => canEnterWing(w.id, role)).map((w) => (
              <div key={w.id} className={styles.wingGroup}>
                <p className={styles.wingHeader}>{w.title.split(" · ")[0]}</p>
                {STATIONS.filter((s) => s.wing === w.id && s.inLists !== false && canEnter(s, role)).map((s) => {
                  const Icon = ROOM_ICONS[s.id];
                  return (
                    <Link
                      key={s.id}
                      href={s.route}
                      className={styles.roomLink}
                      aria-current={s.id === station?.id ? "page" : undefined}
                      onClick={(e) => {
                        // on a phone the menu is open over the page: close it once a room is picked
                        const menu = e.currentTarget.closest<HTMLElement>("[popover]");
                        if (menu?.matches(":popover-open")) menu.hidePopover();
                      }}
                    >
                      {Icon && <Icon />}
                      {s.title}
                    </Link>
                  );
                })}
              </div>
            ))}
          </nav>
          <div className={`${styles.card} ${styles.sideAccount}`}>
            <span className={styles.avatar} aria-hidden="true">
              {initials(name)}
            </span>
            <span className={styles.sideWho}>
              <strong>{name}</strong>
              <span>{role.replace("_", " ")}</span>
            </span>
            {role === "super_admin" && (
              <form action={setView.bind(null, "3d")}>
                <button type="submit" className={`${styles.button} ${styles.iconButton}`} title="Open the 3D HQ">
                  3D
                  <span className="sr-only"> HQ</span>
                </button>
              </form>
            )}
            <form action={toggleTheme}>
              <button type="submit" className={`${styles.button} ${styles.iconButton}`} aria-label={themeLabel} title={themeLabel}>
                {theme === "dark" ? <SunIcon /> : <MoonIcon />}
              </button>
            </form>
            <form action={logOut}>
              <button type="submit" className={`${styles.button} ${styles.iconButton}`} aria-label="Log out" title="Log out">
                <LogOutIcon />
              </button>
            </form>
          </div>
        </aside>
        <main className={styles.listMain}>
          {/* just the title and what the page is for: the sidebar already shows where you are */}
          <header className={styles.panelHeader}>
            <h1 className={styles.panelTitle} id="room-title" tabIndex={-1}>
              {station?.title ?? "ITI AI HQ"}
            </h1>
            {station && <p className={styles.panelDesc}>{station.desc}</p>}
          </header>
          <div className={styles.panelBody}>{body}</div>
        </main>
        {noticeLine}
        <Toaster />
      </div>
    );
  }

  return (
    <div className={styles.hq} ref={hqRef}>
      <a href="#room-title" className={styles.skip}>
        Skip to the page
      </a>
      <HqScene
        role={role}
        theme={theme}
        phtSim={phtSim}
        city={city}
        roomProps={roomProps}
        active={station}
        health={health?.tone ?? null}
        panelOpen={panelOpen}
        onControls={(c) => {
          controls.current = c;
        }}
        onOpenRoom={(s: Station) => router.push(s.route)}
        onOpenUrl={(url) => router.push(url)}
        onBlocked={tell}
        onInteract={() => {
          setDockOpen(false);
          setBarOpen(false);
        }}
        onNoWebgl={() => setNoWebgl(true)}
      />

      <div className={styles.topBar} ref={topBarRef}>
        <div className={styles.topLeft}>
          {brand}
          {healthPill}
        </div>
        {accountBar}
      </div>
      {noticeLine}
      <Toaster />

      {/* Wings dock: every room, grouped by wing; locked ones say so */}
      {!dockOpen && (
        <button
          type="button"
          className={`${styles.card} ${styles.dockToggle}`}
          aria-expanded={false}
          aria-controls="wings-dock"
          onClick={() => setDockOpen(true)}
        >
          ☰ Wings
        </button>
      )}
      <nav
        id="wings-dock"
        aria-label="Wings and rooms"
        className={`${styles.card} ${styles.dock}`}
        data-open={dockOpen ? "" : undefined}
        inert={!dockOpen}
      >
        <div className={styles.dockHead}>
          <strong>HQ wings</strong>
          <button type="button" className={styles.button} onClick={() => setDockOpen(false)}>
            ‹ Hide
          </button>
        </div>
        {WINGS.map((w) => (
          <div key={w.id} className={styles.wingGroup}>
            <p className={styles.wingHeader}>
              {w.title} {!canEnterWing(w.id, role) && <span aria-label="locked">🔒</span>}
            </p>
            {STATIONS.filter((s) => s.wing === w.id && s.inLists !== false).map((s) =>
              canEnter(s, role) ? (
                <Link
                  key={s.id}
                  href={s.route}
                  className={styles.roomLink}
                  aria-current={s.id === station?.id ? "page" : undefined}
                  onClick={() => setDockOpen(false)}
                >
                  {s.title}
                  <span className={styles.roomMeta}>{s.roomObject}</span>
                </Link>
              ) : (
                <span key={s.id} className={`${styles.roomLink} ${styles.roomLocked}`}>
                  {s.title} 🔒<span className={styles.roomMeta}>{s.roomObject}</span>
                </span>
              ),
            )}
          </div>
        ))}
      </nav>

      {/* Camera bar (keyboard: Q / E orbit, R / F tilt, WASD pan, Home reset) */}
      {!barOpen && (
        <button
          type="button"
          className={`${styles.card} ${styles.barToggle}`}
          aria-label="Show the camera controls"
          aria-expanded={false}
          aria-controls="camera-bar"
          onClick={() => setBarOpen(true)}
        >
          ▲
        </button>
      )}
      <div
        id="camera-bar"
        role="toolbar"
        aria-label="Camera"
        className={`${styles.card} ${styles.cameraBar}`}
        data-open={barOpen ? "" : undefined}
        inert={!barOpen}
      >
        <button type="button" className={styles.button} aria-label="Hide the camera controls" onClick={() => setBarOpen(false)}>
          ▼
        </button>
        <button type="button" className={styles.button} onClick={() => controls.current?.orbit(-1)}>
          ↺ Orbit (Q)
        </button>
        <button type="button" className={styles.button} onClick={() => controls.current?.orbit(1)}>
          ↻ Orbit (E)
        </button>
        <button type="button" className={styles.button} onClick={() => controls.current?.tilt(4)}>
          ▲ Tilt (R)
        </button>
        <button type="button" className={styles.button} onClick={() => controls.current?.tilt(-4)}>
          ▼ Tilt (F)
        </button>
        <button type="button" className={styles.button} onClick={() => controls.current?.zoom(0.9)}>
          ＋ Zoom
        </button>
        <button type="button" className={styles.button} onClick={() => controls.current?.zoom(1.11)}>
          － Zoom
        </button>
        <button
          type="button"
          className={styles.button}
          onClick={() => {
            const next = NEXT_WALLS[walls];
            setWalls(next);
            controls.current?.setWalls(next);
          }}
        >
          {WALL_LABELS[walls]}
        </button>
        <button type="button" className={`${styles.button} ${styles.primary}`} onClick={() => controls.current?.reset()}>
          ⌂ Reset (Home)
        </button>
        <span className={styles.hint}>Drag to pan · right-drag to orbit · tap the floor to walk</span>
      </div>

      {/* The open page */}
      {panelOpen ? (
        <aside className={`${styles.card} ${styles.panel}`} aria-label={station?.title ?? "Page"}>
          <div className={styles.panelTop}>
            {header}
            <div className={styles.panelButtons}>
              <button type="button" className={styles.button} onClick={() => controls.current?.focusRoom()}>
                ◎ Focus room
              </button>
              <button type="button" className={styles.button} onClick={() => setPanelOpen(false)}>
                ✕ Hide
              </button>
            </div>
          </div>
          <div className={styles.panelBody}>{body}</div>
        </aside>
      ) : (
        <button type="button" className={`${styles.card} ${styles.panelToggle}`} onClick={() => setPanelOpen(true)}>
          {station?.title ?? "Page"} ›
        </button>
      )}
    </div>
  );
}

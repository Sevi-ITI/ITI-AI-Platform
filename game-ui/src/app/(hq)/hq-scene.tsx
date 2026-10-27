"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef } from "react";
import * as THREE from "three";

import { clockText, phtNow } from "@/hq/pht";
import { CAMERA, CameraController } from "@/hq/scene/camera";
import { buildCity, type City, type CityBlock, disposeCity, layoutCity } from "@/hq/scene/city";
import { buildClockTower, type ClockTower, updateClock } from "@/hq/scene/clock";
import { buildEnvironment, updateTraffic } from "@/hq/scene/environment";
import { recolorTree } from "@/hq/scene/palette";
import { buildStaff, updateStaff } from "@/hq/scene/staff";
import { applySun } from "@/hq/scene/sun";
import {
  animateWorld,
  applyActive,
  applyRole,
  applyTheme,
  buildWorld,
  setBeacon,
  updateWalls,
  type World,
} from "@/hq/scene/world";
import { Xia } from "@/hq/scene/xia";
import { canEnter, canEnterWing, type Role, type Station, STATIONS, type WingId } from "@/hq/stations";
import type { Theme } from "@/hq/theme";

import styles from "./hq.module.css";

export type WallMode = "auto" | "down" | "up";

/** What the camera bar can do to the scene (filled in once the scene runs). */
export type SceneControls = {
  orbit: (direction: 1 | -1) => void;
  tilt: (degrees: number) => void;
  zoom: (factor: number) => void;
  reset: () => void;
  focusRoom: () => void;
  setWalls: (mode: WallMode) => void;
};

type Props = {
  role: Role;
  theme: Theme;
  phtSim: number | null; // simulated time of day in minutes (clock tower), null = live Manila time
  city: CityBlock[]; // V4: the app city blocks (real apps and their linked companies)
  active: Station | undefined;
  health: "ok" | "warn" | "error" | null; // the roof beacon's color (null = not checked yet)
  panelOpen: boolean; // the HUD panel covers the right side: rooms are framed to its left
  onControls: (controls: SceneControls | null) => void; // the camera bar's handle on the scene
  onOpenRoom: (station: Station) => void;
  onOpenUrl: (url: string) => void; // a city block → its app, an office → its company
  onBlocked: (message: string) => void;
  onInteract: () => void;
  onNoWebgl: () => void;
};

type Running = {
  scene: THREE.Scene;
  camera: THREE.PerspectiveCamera;
  controller: CameraController;
  world: World;
  xia: Xia;
  tower: ClockTower;
  city: City | null;
  travel: (appId: string, companyId: string | null) => void; // walk Xia to a city block or office, frame it
};

const NEAR_ROOM = 2.1; // Xia this close to a room after a walk = she opens it

const CITY_FOCUS = { block: 34, office: 18 }; // camera distance when framing a city block / one office

/** Where a city click goes: an office of a company → that company, anything else in a block → its app. */
function cityUrl(appId: string, companyId: string | null): string {
  return companyId ? `/companies#company-${companyId}` : `/apps?q=${encodeURIComponent(appId)}`;
}

function wingAt(x: number, z: number): WingId {
  if (z < 0) return x < 0 ? "monitor" : "knowledge";
  return x < 0 ? "clients" : "admin";
}

/** How far the camera stands from a room it frames: the 12 m clock tower needs more room than a desk. */
function focusDistance(station: Station): number {
  return station.id === "clock" ? 34 : CAMERA.focusDistance;
}

/** Where Xia stands to use a room: 1.1 m in front of it, toward the plaza. */
function standingSpot(station: Station): [number, number] {
  const [x, , z] = station.pos;
  return [x > 0 ? x - 1.1 : x + 1.1, z > 0 ? z - 1.1 : z + 1.1];
}

export default function HqScene(props: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const pinRefs = useRef<Record<string, HTMLElement | null>>({});
  const xiaTagRef = useRef<HTMLDivElement>(null);
  const clockTimeRef = useRef<HTMLSpanElement>(null);
  const cityPinRefs = useRef<Record<string, HTMLElement | null>>({});
  // A city trip opens /apps or /companies: that room's own walk-and-frame must not undo the trip (activeId effect)
  const tripRoom = useRef<{ room: string; at: number } | null>(null);
  // Keyed by content: every server refresh sends a new array, but the city is rebuilt only when the data changes
  const cityKey = JSON.stringify(props.city);
  const placed = useMemo(() => layoutCity(JSON.parse(cityKey) as CityBlock[]), [cityKey]);
  const placedRef = useRef(placed);
  const runningRef = useRef<Running | null>(null);
  const latest = useRef(props); // the animation loop and event handlers read the newest props from here

  useEffect(() => {
    latest.current = props;
  });

  // Build the world once; tear it all down when the HQ view closes.
  useEffect(() => {
    const container = containerRef.current!;
    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: "high-performance" });
    } catch {
      latest.current.onNoWebgl();
      return;
    }
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    container.appendChild(renderer.domElement);

    const motion = window.matchMedia("(prefers-reduced-motion: reduce)");
    const reduced = () => motion.matches;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(CAMERA.fov, 1, 0.5, 200);
    const controller = new CameraController(camera, renderer.domElement, reduced, () => latest.current.onInteract());
    const world = buildWorld(scene);
    const environment = buildEnvironment(scene);
    const xia = new Xia(scene);
    const tower = buildClockTower(scene);
    const staff = buildStaff(scene);
    world.rooms.push(tower.group); // clickable like a room: it opens /clock-tower
    let walls: WallMode = "auto";
    let followXia = false; // the camera follows Xia on walks the person started by tapping the floor
    // V4: Xia walks out to the block (its side facing the hub) or to the office's door; the camera frames it
    const travel = (appId: string, companyId: string | null) => {
      const block = placedRef.current.find((b) => b.block.appId === appId);
      if (!block) return;
      const office = companyId ? block.offices.find((o) => o.company?.companyId === companyId) : undefined;
      const [x, z] = office ? [office.walkX, office.walkZ] : [block.labelX, block.labelZ];
      tripRoom.current = { room: companyId ? "companies" : "apps", at: Date.now() };
      followXia = false;
      xia.walkTo(x, z, reduced(), null, true);
      controller.focusOn(x, z, shift(), office ? CITY_FOCUS.office : CITY_FOCUS.block);
    };
    runningRef.current = { scene, camera, controller, world, xia, tower, city: null, travel };

    const shift = () => (latest.current.panelOpen ? 3.4 : 0.8);
    latest.current.onControls({
      orbit: (direction) => controller.orbitStep(direction),
      tilt: (degrees) => controller.tiltStep(degrees),
      zoom: (factor) => controller.zoomStep(factor),
      reset: () => controller.resetHome(),
      focusRoom: () => {
        const room = latest.current.active;
        if (room) controller.focusOn(room.pos[0], room.pos[2], shift(), focusDistance(room));
      },
      setWalls: (mode) => {
        walls = mode;
      },
    });

    const resize = () => {
      const w = container.clientWidth || window.innerWidth;
      const h = container.clientHeight || window.innerHeight;
      renderer.setSize(w, h);
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
    };
    resize();
    const observer = new ResizeObserver(resize);
    observer.observe(container);

    // A click (not a drag) on a room opens it; on the floor, Xia walks there.
    let down = { x: 0, y: 0 };
    const raycaster = new THREE.Raycaster();
    const onDown = (e: PointerEvent) => {
      down = { x: e.clientX, y: e.clientY };
    };
    const onUp = (e: PointerEvent) => {
      if (e.button !== 0 || e.altKey || Math.hypot(e.clientX - down.x, e.clientY - down.y) > 6) return;
      const { role, onOpenRoom, onBlocked } = latest.current;
      const rect = renderer.domElement.getBoundingClientRect();
      raycaster.setFromCamera(
        new THREE.Vector2(((e.clientX - rect.left) / rect.width) * 2 - 1, -((e.clientY - rect.top) / rect.height) * 2 + 1),
        camera,
      );
      const hit = raycaster.intersectObjects(world.rooms, true)[0];
      const station = STATIONS.find((s) => s.id === hit?.object.userData.stationId);
      if (station) {
        if (canEnter(station, role)) onOpenRoom(station);
        else onBlocked(lockedMessage(station.wing));
        return;
      }
      const city = runningRef.current?.city;
      const cityHit = city ? raycaster.intersectObject(city.group, true)[0] : undefined;
      const appId = cityHit?.object.userData.appId as string | undefined;
      if (appId) {
        const companyId = (cityHit?.object.userData.companyId as string | undefined) ?? null;
        travel(appId, companyId);
        latest.current.onOpenUrl(cityUrl(appId, companyId));
        return;
      }
      const floor = controller.floorPoint(e.clientX, e.clientY);
      if (!floor) return;
      const wing = wingAt(floor.x, floor.z);
      const onPlaza = Math.hypot(floor.x, floor.z) < 2.3;
      if (!onPlaza && !canEnterWing(wing, role)) {
        onBlocked(lockedMessage(wing));
        return;
      }
      followXia = true;
      xia.walkTo(floor.x, floor.z, reduced(), () => {
        followXia = false;
        // Arrived next to a room she may open: open it.
        const near = STATIONS.find((s) => Math.hypot(s.pos[0] - xia.position.x, s.pos[2] - xia.position.y) < NEAR_ROOM);
        const now = latest.current;
        if (near && near.id !== now.active?.id && canEnter(near, now.role)) now.onOpenRoom(near);
      });
    };
    renderer.domElement.addEventListener("pointerdown", onDown);
    renderer.domElement.addEventListener("pointerup", onUp);

    // The loop: move things, draw, then pin the room labels and Xia's tag over their 3D spots.
    const projected = new THREE.Vector3();
    const toCamera = new THREE.Vector3();
    const place = (el: HTMLElement | null, x: number, y: number, z: number) => {
      if (!el) return;
      projected.set(x, y, z).project(camera);
      if (projected.z > 1) {
        el.style.display = "none";
        return;
      }
      el.style.display = "";
      const px = Math.round((projected.x * 0.5 + 0.5) * container.clientWidth);
      const py = Math.round((-projected.y * 0.5 + 0.5) * container.clientHeight);
      el.style.transform = `translate3d(${px}px, ${py}px, 0) translate(-50%, -100%)`;
    };
    let frame = 0;
    let last = performance.now();
    let lastSecond = -1; // the clock's hands and label move once a second, the sun once a minute
    let lastSunMinute = -1;
    const loop = (now: number) => {
      frame = requestAnimationFrame(loop);
      const dt = Math.min((now - last) / 1000, 0.1);
      last = now;
      if (document.hidden) return;
      const seconds = now / 1000;
      const still = reduced();

      const second = Math.floor(Date.now() / 1000);
      if (second !== lastSecond) {
        lastSecond = second;
        const pht = phtNow(latest.current.phtSim);
        updateClock(tower, pht);
        if (clockTimeRef.current) clockTimeRef.current.textContent = clockText(pht, false);
        if (pht.minutes !== lastSunMinute) {
          lastSunMinute = pht.minutes;
          applySun(world, pht, world.theme);
        }
      }

      xia.update(dt, seconds, still);
      if (followXia && xia.isMoving && !controller.isDragging) {
        controller.followTo(xia.position.x, xia.position.y, latest.current.panelOpen ? 2.8 : 0.5);
      }
      if (!still) {
        updateTraffic(environment, dt);
        updateStaff(staff, dt);
        if (runningRef.current?.city) updateStaff(runningRef.current.city.walkers, dt);
        animateWorld(world, seconds);
      }
      controller.update(dt);
      toCamera.subVectors(camera.position, controller.currentFocus).setY(0).normalize();
      updateWalls(world, toCamera, walls, still);
      renderer.render(scene, camera);

      for (const st of STATIONS) place(pinRefs.current[st.id], st.pos[0], st.pos[1] + 0.7, st.pos[2]);
      place(xiaTagRef.current, xia.position.x, 2.05, xia.position.y);
      for (const block of placedRef.current) {
        place(cityPinRefs.current[`b:${block.block.appId}`], block.labelX, 6.5, block.labelZ);
        for (const office of block.offices) {
          if (office.company) {
            place(cityPinRefs.current[`o:${block.block.appId}:${office.company.companyId}`], office.x, office.h + 1.6, office.z);
          }
        }
      }
    };
    frame = requestAnimationFrame(loop);

    return () => {
      cancelAnimationFrame(frame);
      observer.disconnect();
      controller.dispose();
      renderer.domElement.removeEventListener("pointerdown", onDown);
      renderer.domElement.removeEventListener("pointerup", onUp);
      scene.traverse((object) => {
        if (object instanceof THREE.Mesh) {
          object.geometry.dispose();
          const materials: THREE.Material[] = Array.isArray(object.material) ? object.material : [object.material];
          for (const m of materials) m.dispose();
        }
      });
      renderer.dispose();
      renderer.domElement.remove();
      runningRef.current = null;
      latest.current.onControls(null);
    };
    // Built once: later prop changes reach the loop through `latest`.
  }, []);

  useEffect(() => {
    if (runningRef.current) applyRole(runningRef.current.world, props.role);
  }, [props.role]);

  // The city: built when the scene starts and again whenever the apps or their companies change
  useEffect(() => {
    placedRef.current = placed;
    const running = runningRef.current;
    if (!running) return;
    if (running.city) disposeCity(running.scene, running.city);
    running.city = buildCity(running.scene, placed.map((p) => p.block));
    recolorTree(running.city.group, running.world.theme);
  }, [placed]);

  useEffect(() => {
    if (runningRef.current) setBeacon(runningRef.current.world, props.health);
  }, [props.health]);

  // Recolor in place (no rebuild), so the camera and Xia stay where they are; the light follows the (simulated) time.
  useEffect(() => {
    const running = runningRef.current;
    if (!running) return;
    applyTheme(running.scene, running.world, props.theme);
    const pht = phtNow(props.phtSim);
    applySun(running.world, pht, props.theme);
    updateClock(running.tower, pht);
  }, [props.theme, props.phtSim]);

  // A new room (from any click, link or back/forward): light its ring, walk Xia there, frame it.
  const activeId = props.active?.id;
  useEffect(() => {
    const running = runningRef.current;
    const room = STATIONS.find((s) => s.id === activeId);
    if (!running) return;
    applyActive(running.world, activeId);
    if (!room) return;
    const trip = tripRoom.current;
    tripRoom.current = null;
    if (trip && trip.room === room.id && Date.now() - trip.at < 3000) return; // a city trip: Xia is already on her way
    const [x, z] = standingSpot(room);
    const instant = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    running.xia.walkTo(x, z, instant);
    running.controller.focusOn(room.pos[0], room.pos[2], latest.current.panelOpen ? 3.4 : 0.8, focusDistance(room));
  }, [activeId]);

  return (
    <>
      <div
        ref={containerRef}
        className={styles.viewport}
        role="img"
        aria-label="The ITI AI HQ in 3D. Use the room labels or the wings list to open a page."
      />
      <div className={styles.pins} role="group" aria-label="Rooms">
        {STATIONS.map((st) => {
          const allowed = canEnter(st, props.role);
          const current = st.id === activeId;
          const setRef = (el: HTMLElement | null) => {
            pinRefs.current[st.id] = el;
          };
          return allowed ? (
            <Link
              key={st.id}
              ref={setRef}
              href={st.route}
              prefetch={false}
              className={styles.pin}
              aria-current={current ? "page" : undefined}
            >
              <span className={styles.pinDot} aria-hidden="true" />
              {st.title}
              {st.id === "clock" && <span ref={clockTimeRef} className={styles.pinTime} />}
            </Link>
          ) : (
            <button
              key={st.id}
              ref={setRef}
              type="button"
              className={`${styles.pin} ${styles.pinLocked}`}
              onClick={() => props.onBlocked(lockedMessage(st.wing))}
            >
              <span className={styles.pinDot} aria-hidden="true" />
              {st.title}
              <span aria-label="locked for your role">🔒</span>
            </button>
          );
        })}
        <div ref={xiaTagRef} className={styles.xiaTag} aria-hidden="true">
          ◆ Xia
        </div>
      </div>
      <div className={styles.pins} role="group" aria-label="App city blocks">
        {placed.map((block) => {
          const appId = block.block.appId;
          return [
            <Link
              key={`b:${appId}`}
              ref={(el) => {
                cityPinRefs.current[`b:${appId}`] = el;
              }}
              href={cityUrl(appId, null)}
              prefetch={false}
              className={`${styles.pin} ${styles.pinBlock}`}
              onClick={() => runningRef.current?.travel(appId, null)}
            >
              <span className={styles.pinDot} aria-hidden="true" />
              {block.block.name}
            </Link>,
            ...block.offices.flatMap((office) => {
              const company = office.company;
              if (!company) return [];
              const key = `o:${appId}:${company.companyId}`;
              return [
                <Link
                  key={key}
                  ref={(el) => {
                    cityPinRefs.current[key] = el;
                  }}
                  href={cityUrl(appId, company.companyId)}
                  prefetch={false}
                  className={styles.pin}
                  onClick={() => runningRef.current?.travel(appId, company.companyId)}
                >
                  {company.name}
                  <span className="sr-only"> (an office in {block.block.name})</span>
                </Link>,
              ];
            }),
          ];
        })}
      </div>
    </>
  );
}

export function lockedMessage(wing: WingId): string {
  return wing === "admin"
    ? "The Engine Room is for super admins only."
    : "Testers can only use the Chat desk in the Library.";
}

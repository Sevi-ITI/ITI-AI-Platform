import * as THREE from "three";

import { STATIONS } from "@/hq/stations";

// The room props that follow real data (super admins' 3D view; loaded with the city in load-hq.ts):
// - Documents: one bookshelf per collection, more books the more files it holds (an empty shelf = no files);
// - Companies: one building model per company on the table, green while it has an active key, grey without;
// - Tools & MCP: one pipe per MCP connection on the machine (glowing green = usable, grey = off or not set up) and one
//   valve per tool (green = on and used, amber = waiting for approval, red = switched off, grey = on but no app uses it).
// The bases (the companies table, the tools machine) stay in world.ts. Every mesh carries userData.stationId, so a
// click opens the room like any prop; a shelf or a model also carries userData.href (that collection or company).
// Built in dark colors like the rest of the scene; the caller applies the theme. Rebuilt when the data changes.

export type RoomProps = {
  collections: { name: string; files: number }[];
  companies: { id: string; name: string; activeKeys: number }[];
  connections: { name: string; usable: boolean }[];
  tools: { name: string; on: boolean; inUse: boolean; waiting: boolean }[];
};

export const EMPTY_PROPS: RoomProps = { collections: [], companies: [], connections: [], tools: [] };

// The most of each that fits its room; the room's page lists them all.
const MAX = { shelves: 6, models: 6, pipes: 4, valves: 12 };

const COLORS = { accent: 0x6e76f0, ok: 0x5cc98f, warn: 0xe9b25c, cream: 0xf4f1ea, error: 0xf07c7c };
const SHELF = 0x283868; // furniture navy: palette.ts turns it to sand in light mode
const IDLE = 0x5f6878; // grey: an idle company, a pipe or valve that does nothing
const IDLE_LIGHT = 0xa59d8f;
const BOOK_COLORS = [COLORS.accent, COLORS.ok, COLORS.warn, COLORS.cream];

function material(color: number, extra: THREE.MeshStandardMaterialParameters = {}) {
  const m = new THREE.MeshStandardMaterial({ color, roughness: 0.45, ...extra });
  if (color === IDLE) m.userData.light = IDLE_LIGHT;
  return m;
}

function glow(color: number, intensity: number) {
  return material(color, { emissive: color, emissiveIntensity: intensity, roughness: 0.25 });
}

function mesh(geometry: THREE.BufferGeometry, mat: THREE.Material, x: number, y: number, z: number) {
  const m = new THREE.Mesh(geometry, mat);
  m.position.set(x, y, z);
  return m;
}

/** Books on a shelf: none for an empty collection, up to six for a big one (a few files already show three). */
export function bookCount(files: number): number {
  if (files <= 0) return 0;
  if (files <= 2) return files;
  return files < 10 ? 3 : files < 25 ? 4 : files < 50 ? 5 : 6;
}

function documents(collections: RoomProps["collections"]): THREE.Group {
  const g = new THREE.Group();
  const shown = collections.slice(0, MAX.shelves);
  shown.forEach((c, i) => {
    const shelf = new THREE.Group();
    shelf.position.x = (i - (shown.length - 1) / 2) * 0.8;
    shelf.add(mesh(new THREE.BoxGeometry(0.72, 1.9, 0.42), material(SHELF, { roughness: 0.6 }), 0, 0.95, 0));
    for (let b = 0; b < bookCount(c.files); b++) {
      const book = mesh(
        new THREE.BoxGeometry(0.11, 0.34, 0.28),
        material(BOOK_COLORS[(i + b) % BOOK_COLORS.length], { roughness: 0.4 }),
        -0.2 + (b % 3) * 0.16,
        1.42 - Math.floor(b / 3) * 0.5,
        0.08,
      );
      shelf.add(book);
    }
    shelf.traverse((child) => {
      child.userData.href = `/documents?collection=${encodeURIComponent(c.name)}`;
    });
    g.add(shelf);
  });
  return g;
}

function companies(list: RoomProps["companies"]): THREE.Group {
  const g = new THREE.Group();
  const shown = list.slice(0, MAX.models);
  const perRow = Math.min(3, shown.length);
  const rows = Math.ceil(shown.length / 3);
  shown.forEach((c, i) => {
    const active = c.activeKeys > 0;
    const h = 0.45 + Math.min(c.activeKeys, 4) * 0.12; // taller with more active keys
    const inRow = i < 3 ? perRow : shown.length - 3;
    const model = mesh(
      new THREE.BoxGeometry(0.38, h, 0.38),
      active ? material(COLORS.ok, { emissive: COLORS.ok, emissiveIntensity: 0.25, roughness: 0.35 }) : material(IDLE),
      ((i % 3) - (inRow - 1) / 2) * 0.68,
      0.72 + h / 2,
      rows === 1 ? 0 : (Math.floor(i / 3) - 0.5) * 0.65,
    );
    model.userData.href = `/companies#company-${encodeURIComponent(c.id)}`;
    g.add(model);
  });
  return g;
}

function tools(connections: RoomProps["connections"], list: RoomProps["tools"]): THREE.Group {
  const g = new THREE.Group();
  const pipes = connections.slice(0, MAX.pipes);
  pipes.forEach((c, i) => {
    const x = (i - (pipes.length - 1) / 2) * 0.6;
    g.add(mesh(new THREE.CylinderGeometry(0.14, 0.14, 1.9, 16), c.usable ? glow(COLORS.ok, 0.6) : material(IDLE), x, 1.55, -0.35));
  });
  const valves = list.slice(0, MAX.valves);
  valves.forEach((t, i) => {
    const inRow = i < 6 ? Math.min(6, valves.length) : valves.length - 6;
    const color = t.waiting ? COLORS.warn : !t.on ? COLORS.error : t.inUse ? COLORS.ok : IDLE;
    const valve = mesh(
      new THREE.TorusGeometry(0.12, 0.04, 10, 20),
      color === IDLE ? material(IDLE) : glow(color, 0.45),
      ((i % 6) - (inRow - 1) / 2) * 0.33,
      i < 6 ? 1.05 : 0.6,
      0.72,
    );
    g.add(valve);
  });
  return g;
}

/** Build the three rooms' live parts at their stations. */
export function buildRoomProps(scene: THREE.Scene, data: RoomProps): THREE.Group {
  const root = new THREE.Group();
  const place = (id: string, group: THREE.Group) => {
    const st = STATIONS.find((s) => s.id === id)!;
    group.position.set(st.pos[0], 0.14, st.pos[2]);
    group.traverse((child) => {
      child.userData.stationId = id;
      if (child instanceof THREE.Mesh) {
        child.castShadow = true;
        child.receiveShadow = true;
      }
    });
    root.add(group);
  };
  place("documents", documents(data.collections));
  place("companies", companies(data.companies));
  place("tools", tools(data.connections, data.tools));
  scene.add(root);
  return root;
}

/** Take the props out of the scene and free their GPU memory (before building them again with new data). */
export function disposeRoomProps(scene: THREE.Scene, root: THREE.Group): void {
  scene.remove(root);
  root.traverse((object) => {
    if (object instanceof THREE.Mesh) {
      object.geometry.dispose();
      (object.material as THREE.Material).dispose();
    }
  });
}

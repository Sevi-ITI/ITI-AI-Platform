import * as THREE from "three";

import { recolor, recolorTree, SKY } from "@/hq/scene/palette";
import { canEnterWing, type Role, STATIONS, type WingId } from "@/hq/stations";
import type { Theme } from "@/hq/theme";

// The HQ building: lights, floor, four wings, walls that drop when they hide the view, a ring under every room
// and each room's prop (a wall of screens for Overview, a vault for Apps & keys...). Built in dark theme colors;
// applyTheme swaps them (palette.ts). The props are fixed shapes for now (G2): bookshelves and company models
// follow real data in later steps.

export type World = {
  /** Room props, clickable: each mesh carries userData.stationId. */
  rooms: THREE.Object3D[];
  walls: THREE.Mesh[];
  rings: Record<string, THREE.Mesh<THREE.RingGeometry, THREE.MeshBasicMaterial>>;
  wingFloors: Record<WingId, THREE.Mesh<THREE.BoxGeometry, THREE.MeshStandardMaterial>>;
  beacon: THREE.Mesh<THREE.SphereGeometry, THREE.MeshStandardMaterial>;
  beaconRing: THREE.Mesh<THREE.TorusGeometry, THREE.MeshStandardMaterial>;
  beaconAlarm: boolean; // pulses faster when not "ok"
  screens: THREE.Mesh<THREE.BoxGeometry, THREE.MeshStandardMaterial>[];
  needles: THREE.Mesh[];
  blastDoor: THREE.Mesh;
  hemi: THREE.HemisphereLight;
  sun: THREE.DirectionalLight;
  grids: Record<Theme, THREE.GridHelper>; // a grid's colors are baked in, so each theme has its own
  theme: Theme;
};

const COLORS = {
  accent: 0x6e76f0,
  ok: 0x5cc98f,
  warn: 0xe9b25c,
  cream: 0xf4f1ea,
  error: 0xf07c7c,
  wall: 0x202d56,
  lockedFloor: 0x070c1d,
};

const WING_FLOORS: { id: WingId; x: number; z: number; color: number }[] = [
  { id: "monitor", x: -5.5, z: -5.5, color: 0x162244 },
  { id: "knowledge", x: 5.5, z: -5.5, color: 0x182548 },
  { id: "clients", x: -5.5, z: 5.5, color: 0x152040 },
  { id: "admin", x: 5.5, z: 5.5, color: 0x1b1f3c },
];

// x, z, width, depth, outward normal (x, z): a wall drops when its normal points at the camera
const WALLS: [number, number, number, number, number, number][] = [
  [-5.5, -10.3, 9.6, 0.28, 0, -1],
  [5.5, -10.3, 9.6, 0.28, 0, -1],
  [-5.5, 10.3, 9.6, 0.28, 0, 1],
  [5.5, 10.3, 9.6, 0.28, 0, 1],
  [-10.3, -5.5, 0.28, 9.6, -1, 0],
  [-10.3, 5.5, 0.28, 9.6, -1, 0],
  [10.3, -5.5, 0.28, 9.6, 1, 0],
  [10.3, 5.5, 0.28, 9.6, 1, 0],
  [0, -6.2, 0.24, 7.2, 1, 0],
  [0, 6.2, 0.24, 7.2, 1, 0],
  [-6.2, 0, 7.2, 0.24, 0, 1],
  [6.2, 0, 7.2, 0.24, 0, 1],
];

export const WALL_HEIGHT = 3.3;

function material(color: number, extra: THREE.MeshStandardMaterialParameters = {}) {
  return new THREE.MeshStandardMaterial({ color, roughness: 0.5, ...extra });
}

function glow(color: number, intensity: number) {
  return material(color, { emissive: color, emissiveIntensity: intensity, roughness: 0.25 });
}

function mesh<G extends THREE.BufferGeometry, M extends THREE.Material>(geometry: G, mat: M, x = 0, y = 0, z = 0) {
  const m = new THREE.Mesh(geometry, mat);
  m.position.set(x, y, z);
  return m;
}

export function buildWorld(scene: THREE.Scene): World {
  scene.background = new THREE.Color(0x0a1128);

  // three.js lights are physical since r155: the mock's (r128) intensities × π give the same brightness.
  const hemi = new THREE.HemisphereLight(0xdde6ff, 0x111a34, 0.85 * Math.PI);
  hemi.position.set(0, 30, 0);
  scene.add(hemi);
  const sun = new THREE.DirectionalLight(0xfffdf8, 0.95 * Math.PI);
  sun.position.set(18, 28, 16);
  sun.castShadow = true;
  sun.shadow.mapSize.set(1024, 1024);
  Object.assign(sun.shadow.camera, { near: 5, far: 75, left: -18, right: 18, top: 18, bottom: -18 });
  scene.add(sun);

  // Plinth, grid, the central plaza and its beacon (accent until the first health check, then setBeacon)
  const plinth = mesh(new THREE.BoxGeometry(24, 0.6, 24), material(0x111a34, { roughness: 0.85 }), 0, -0.3, 0);
  plinth.receiveShadow = true;
  scene.add(plinth);
  const grids: World["grids"] = {
    dark: new THREE.GridHelper(24, 24, COLORS.accent, 0x1e2a4a),
    light: new THREE.GridHelper(24, 24, 0x9a6b12, 0xd5cbb8),
  };
  grids.light.visible = false;
  for (const grid of Object.values(grids)) {
    grid.position.y = 0.01;
    scene.add(grid);
  }
  scene.add(mesh(new THREE.CylinderGeometry(2.1, 2.3, 0.2, 24), material(0x1e2b52, { roughness: 0.6 }), 0, 0.1, 0));
  const pylon = mesh(
    new THREE.CylinderGeometry(0.28, 0.45, 4.6, 16),
    material(0x26335e, { roughness: 0.4, metalness: 0.3 }),
    0,
    2.3,
    0,
  );
  pylon.castShadow = true;
  scene.add(pylon);
  const beacon = mesh(new THREE.SphereGeometry(0.62, 24, 24), glow(COLORS.accent, 0.6), 0, 4.9, 0);
  scene.add(beacon);
  const beaconRing = mesh(new THREE.TorusGeometry(0.95, 0.06, 12, 32), glow(COLORS.accent, 0.5), 0, 4.9, 0);
  beaconRing.rotation.x = Math.PI / 2;
  scene.add(beaconRing);

  const wingFloors = {} as World["wingFloors"];
  for (const wing of WING_FLOORS) {
    const floor = mesh(new THREE.BoxGeometry(9.6, 0.14, 9.6), material(wing.color, { roughness: 0.75 }), wing.x, 0.07, wing.z);
    floor.receiveShadow = true;
    floor.userData.color = wing.color;
    scene.add(floor);
    wingFloors[wing.id] = floor;
  }

  const walls = WALLS.map(([x, z, w, d, nx, nz]) => {
    const wall = mesh(new THREE.BoxGeometry(w, WALL_HEIGHT, d), material(COLORS.wall, { roughness: 0.7 }), x, WALL_HEIGHT / 2, z);
    wall.castShadow = true;
    wall.receiveShadow = true;
    wall.userData.normal = new THREE.Vector3(nx, 0, nz);
    scene.add(wall);
    return wall;
  });

  const rings = {} as World["rings"];
  for (const st of STATIONS) {
    if (st.id === "clock") continue; // outside the building, on its own pedestal (clock.ts)
    const ring = new THREE.Mesh(
      new THREE.RingGeometry(1.35, 1.58, 32),
      new THREE.MeshBasicMaterial({ color: COLORS.accent, side: THREE.DoubleSide, transparent: true, opacity: 0.22 }),
    );
    ring.rotation.x = -Math.PI / 2;
    ring.position.set(st.pos[0], 0.16, st.pos[2]);
    scene.add(ring);
    rings[st.id] = ring;
  }

  const rooms: THREE.Object3D[] = [];
  const screens: World["screens"] = [];
  const needles: THREE.Mesh[] = [];
  const room = (id: string, group: THREE.Group) => {
    const st = STATIONS.find((s) => s.id === id)!;
    group.position.set(st.pos[0], 0.14, st.pos[2]);
    group.traverse((child) => {
      child.userData.stationId = id;
      if (child instanceof THREE.Mesh) {
        child.castShadow = true;
        child.receiveShadow = true;
      }
    });
    scene.add(group);
    rooms.push(group);
  };

  // Overview: a desk and a wall of six live screens
  const overview = new THREE.Group();
  overview.add(mesh(new THREE.BoxGeometry(2.6, 0.75, 1.2), material(0x263563), 0, 0.38, 0));
  for (let row = 0; row < 2; row++) {
    for (let col = -1; col <= 1; col++) {
      const screen = mesh(
        new THREE.BoxGeometry(0.76, 0.48, 0.08),
        material(COLORS.accent, { emissive: 0x4b56d2, emissiveIntensity: 0.65, roughness: 0.25 }),
        col * 0.84,
        1.15 + row * 0.58,
        -0.35,
      );
      overview.add(screen);
      screens.push(screen);
    }
  }
  room("overview", overview);

  // Performance: three dials with swinging needles
  const performance = new THREE.Group();
  performance.add(mesh(new THREE.BoxGeometry(2.5, 0.35, 1.3), material(0x223059, { roughness: 0.6 }), 0, 0.18, 0));
  [-0.75, 0, 0.75].forEach((x, i) => {
    performance.add(mesh(new THREE.CylinderGeometry(0.34, 0.36, 1.25, 20), material(0x2e3f73, { roughness: 0.4 }), x, 0.85, 0));
    const needle = mesh(new THREE.BoxGeometry(0.06, 0.32, 0.06), glow(COLORS.ok, 0.5), x, 1.25, 0.36);
    needle.userData.phase = i * 1.3;
    performance.add(needle);
    needles.push(needle);
  });
  room("performance", performance);

  // Request log: a mail chute, its tube and a strip of ticker tape
  const requests = new THREE.Group();
  requests.add(mesh(new THREE.CylinderGeometry(0.55, 0.65, 1.1, 20), material(0x2b3a6b), 0, 0.55, 0));
  requests.add(mesh(new THREE.CylinderGeometry(0.18, 0.18, 2.6, 16), material(COLORS.warn, { metalness: 0.5, roughness: 0.3 }), -0.25, 1.5, -0.2));
  requests.add(mesh(new THREE.BoxGeometry(0.95, 0.12, 0.45), material(COLORS.cream, { roughness: 0.6 }), 0.2, 1.18, 0.1));
  room("requests", requests);

  // Documents: four bookshelves (one per collection later), a few books each
  const documents = new THREE.Group();
  const bookColors = [COLORS.accent, COLORS.ok, COLORS.warn, COLORS.cream];
  for (let shelf = 0; shelf < 4; shelf++) {
    const x = (shelf - 1.5) * 0.85;
    documents.add(mesh(new THREE.BoxGeometry(0.72, 1.9, 0.42), material(0x283868, { roughness: 0.6 }), x, 0.95, 0));
    for (let b = 0; b < 3 + (shelf % 2); b++) {
      documents.add(
        mesh(
          new THREE.BoxGeometry(0.11, 0.34, 0.28),
          material(bookColors[(shelf + b) % bookColors.length], { roughness: 0.4 }),
          x - 0.22 + b * 0.13,
          1.15 + (b % 2) * 0.42,
          0.08,
        ),
      );
    }
  }
  room("documents", documents);

  // Chat: a curved reception desk with the assistant behind it
  const chat = new THREE.Group();
  chat.add(mesh(new THREE.CylinderGeometry(1.15, 1.2, 0.82, 24, 1, false, 0, Math.PI * 1.35), material(0x2c3d70), 0, 0.41, 0));
  chat.add(mesh(new THREE.CylinderGeometry(0.24, 0.3, 0.7, 16), material(COLORS.accent, { roughness: 0.3 }), 0, 1.05, -0.2));
  chat.add(
    mesh(
      new THREE.SphereGeometry(0.24, 20, 20),
      material(COLORS.cream, { emissive: COLORS.accent, emissiveIntensity: 0.25 }),
      0,
      1.62,
      -0.2,
    ),
  );
  room("chat", chat);

  // Companies: a table of building models (one per company later)
  const companies = new THREE.Group();
  companies.add(mesh(new THREE.BoxGeometry(2.5, 0.72, 1.8), material(0x243461), 0, 0.36, 0));
  for (let i = 0; i < 4; i++) {
    const h = 0.45 + (i % 3) * 0.22;
    companies.add(
      mesh(
        new THREE.BoxGeometry(0.38, h, 0.38),
        material(i === 0 ? COLORS.accent : COLORS.cream, { roughness: 0.35 }),
        ((i % 3) - 1) * 0.68,
        0.72 + h / 2,
        (Math.floor(i / 3) - 0.5) * 0.65,
      ),
    );
  }
  room("companies", companies);

  // Apps & keys: a vault with a brass wheel
  const apps = new THREE.Group();
  apps.add(mesh(new THREE.BoxGeometry(1.5, 1.85, 1.1), material(0x24325c, { metalness: 0.45, roughness: 0.35 }), 0, 0.93, 0));
  const wheel = mesh(new THREE.CylinderGeometry(0.38, 0.38, 0.12, 20), material(COLORS.warn, { metalness: 0.6, roughness: 0.25 }), 0, 1, 0.6);
  wheel.rotation.x = Math.PI / 2;
  apps.add(wheel);
  room("apps", apps);

  // Users & chats: a resident board and a visitor-book lectern
  const users = new THREE.Group();
  users.add(mesh(new THREE.BoxGeometry(1.8, 1.5, 0.22), material(0x263663), 0, 1.05, -0.2));
  users.add(mesh(new THREE.BoxGeometry(0.75, 0.95, 0.55), material(COLORS.cream), 0, 0.48, 0.45));
  room("users", users);

  // Accounts: a badge office with a glowing badge
  const accounts = new THREE.Group();
  accounts.add(mesh(new THREE.BoxGeometry(1.7, 1.6, 1.2), material(0x293766), 0, 0.8, 0));
  accounts.add(mesh(new THREE.BoxGeometry(0.55, 0.75, 0.08), glow(COLORS.ok, 0.35), 0, 1.85, 0));
  room("accounts", accounts);

  // Tools & MCP: a machine with three MCP pipes and four tool valves
  const tools = new THREE.Group();
  tools.add(mesh(new THREE.BoxGeometry(2.2, 1.35, 1.4), material(0x23305a, { metalness: 0.35, roughness: 0.45 }), 0, 0.68, 0));
  for (const x of [-0.65, 0, 0.65]) {
    tools.add(mesh(new THREE.CylinderGeometry(0.14, 0.14, 1.9, 16), glow(COLORS.ok, 0.6), x, 1.55, -0.35));
  }
  for (const x of [-0.75, -0.25, 0.25, 0.75]) {
    tools.add(mesh(new THREE.TorusGeometry(0.18, 0.05, 10, 20), glow(COLORS.accent, 0.4), x, 1.05, 0.75));
  }
  room("tools", tools);

  // The Engine Room's blast door, shown to anyone who may not enter the Admin wing
  const blastDoor = mesh(
    new THREE.BoxGeometry(2.6, 2.8, 0.26),
    material(COLORS.error, { emissive: 0xb3261e, emissiveIntensity: 0.35, roughness: 0.4 }),
    2.4,
    1.4,
    2.4,
  );
  blastDoor.rotation.y = Math.PI / 4;
  blastDoor.visible = false;
  scene.add(blastDoor);

  return {
    rooms,
    walls,
    rings,
    wingFloors,
    beacon,
    beaconRing,
    beaconAlarm: false,
    screens,
    needles,
    blastDoor,
    hemi,
    sun,
    grids,
    theme: "dark",
  };
}

/** Swap every color in the scene (background, grid, meshes) to the theme's; the lights follow with applySun
 *  (sun.ts). The camera and Xia stay put. */
export function applyTheme(scene: THREE.Scene, world: World, theme: Theme): void {
  world.theme = theme;
  (scene.background as THREE.Color).setHex(SKY[theme].background);
  world.grids.dark.visible = theme === "dark";
  world.grids.light.visible = theme === "light";
  recolorTree(scene, theme);
}

const BEACON_COLORS = { ok: COLORS.ok, warn: COLORS.warn, error: COLORS.error };

/** The roof beacon shows the system's health (null = not checked yet: accent). The top bar's pill says it in words. */
export function setBeacon(world: World, tone: "ok" | "warn" | "error" | null): void {
  const color = tone ? BEACON_COLORS[tone] : COLORS.accent;
  for (const m of [world.beacon.material, world.beaconRing.material]) {
    m.userData.dark = color;
    m.userData.darkEmissive = color;
    recolor(m, world.theme);
  }
  world.beaconAlarm = tone === "warn" || tone === "error";
}

/** Dim the wings this role may not enter and close the blast door for non-super-admins. */
export function applyRole(world: World, role: Role): void {
  for (const [wing, floor] of Object.entries(world.wingFloors) as [WingId, World["wingFloors"][WingId]][]) {
    floor.material.userData.dark = canEnterWing(wing, role) ? floor.userData.color : COLORS.lockedFloor;
    recolor(floor.material, world.theme);
  }
  world.blastDoor.visible = !canEnterWing("admin", role);
}

/** Light up the ring of the open room. */
export function applyActive(world: World, stationId: string | undefined): void {
  for (const [id, ring] of Object.entries(world.rings)) {
    const active = id === stationId;
    ring.material.opacity = active ? 0.92 : 0.22;
    ring.scale.setScalar(active ? 1.14 : 1);
  }
}

/** Lower the walls between the camera and the focus ("auto"), all of them ("down") or none ("up"). */
export function updateWalls(
  world: World,
  toCamera: THREE.Vector3,
  mode: "auto" | "down" | "up",
  instant: boolean,
): void {
  for (const wall of world.walls) {
    const cut = mode === "down" || (mode === "auto" && (wall.userData.normal as THREE.Vector3).dot(toCamera) > 0.18);
    const target = cut ? 0.12 : 1;
    if (Math.abs(wall.scale.y - target) > 0.002) {
      wall.scale.y = instant ? target : THREE.MathUtils.lerp(wall.scale.y, target, 0.18);
      wall.position.y = (WALL_HEIGHT * wall.scale.y) / 2;
    }
  }
}

/** Idle life: the beacon ring turns, screens flicker, needles swing. Skipped when motion is reduced. */
export function animateWorld(world: World, seconds: number): void {
  world.beaconRing.rotation.z = seconds * 1.4;
  world.beaconRing.scale.setScalar(
    world.beaconAlarm ? 1 + Math.sin(seconds * 6) * 0.16 : 1 + Math.sin(seconds * 2.5) * 0.06,
  );
  world.screens.forEach((screen, i) => {
    screen.material.emissiveIntensity = 0.45 + 0.35 * Math.sin(seconds * 3.2 + i * 1.7);
  });
  for (const needle of world.needles) {
    needle.rotation.z = Math.sin(seconds * 2.1 + (needle.userData.phase as number)) * 0.55;
  }
}

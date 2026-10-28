import * as THREE from "three";

import { instanced, type Place } from "@/hq/scene/instanced";
import { buildLotPark } from "@/hq/scene/parks";
import { buildWalkers, type Walker } from "@/hq/scene/staff";

// V4, from the design mock: the app city blocks around the HQ. One block per real app (A to Z by id, up to 5 spots:
// west, south, east, south-west, south-east; north is the flyover; a spot no app uses is a park), 3 rows × 5 columns of offices each (Vince: the
// south block too, every door facing the hub). The offices nearest the hub hold the companies the app is linked to,
// lit and labeled; every other lot is a construction site (no building, no beacon: Vince, 2026-10-28), so only a real
// company has an office. Each block has
// inner streets, trees, bins and its app engineer walking the street. Six building styles and three door styles,
// picked from a fixed seed, so a block looks the same on every load. Clicks: an office of a company → that company,
// anything else in the block → that app (hq-scene.tsx reads userData.appId / companyId). Built in dark colors; the
// theme swaps them (palette.ts: userData.light etc.). Outside the sun's shadow box, so nothing casts shadows here.

export type CityOffice = { companyId: string; name: string };

export type CityBlock = { appId: string; name: string; offices: CityOffice[] };

type Slot = { x: number; z: number; w: number; d: number; accent: number; facesNorth: boolean };

export const SLOTS: Slot[] = [
  { x: -39.28, z: 0, w: 34, d: 28.24, accent: 0x6e76f0, facesNorth: false }, // west
  { x: 0, z: 36.4, w: 30, d: 28.24, accent: 0x5cc98f, facesNorth: true }, // south: 30 m wide to clear the side roads
  { x: 39.28, z: 0, w: 34, d: 28.24, accent: 0xe9b25c, facesNorth: false }, // east
  { x: -39.28, z: 36.4, w: 34, d: 28.24, accent: 0xf07c7c, facesNorth: true }, // south-west
  { x: 39.28, z: 36.4, w: 34, d: 28.24, accent: 0x6e76f0, facesNorth: true }, // south-east
];

const ROWS = 3;
const COLS = 5;
const STREET_W = 1.25; // north-south streets between the columns
const STREET_D = 1.85; // east-west streets between the rows
const HEIGHTS = [3.95, 2.85, 3.35, 2.35, 4.35, 2.65, 3.6];

export type PlacedOffice = {
  company: CityOffice | null; // null = a construction site
  x: number; // world position of the office's center
  z: number;
  h: number; // its height (the label floats above)
  walkX: number; // where Xia stands, at its door
  walkZ: number;
  seed: number;
  row: number;
  doorSign: 1 | -1; // which z side the door is on
};

export type PlacedBlock = { block: CityBlock; slot: Slot; index: number; offices: PlacedOffice[]; labelX: number; labelZ: number };

function metrics(slot: Slot) {
  const cellW = (slot.w - (COLS - 1) * STREET_W) / COLS;
  const cellD = (slot.d - (ROWS - 1) * STREET_D) / ROWS;
  return { cellW, cellD, colStep: cellW + STREET_W, rowStep: cellD + STREET_D };
}

/** Where every block and office goes (pure: the 3D builder and the labels both use it). */
export function layoutCity(blocks: CityBlock[]): PlacedBlock[] {
  return blocks.slice(0, SLOTS.length).map((block, index) => {
    const slot = SLOTS[index];
    const m = metrics(slot);
    const offices: PlacedOffice[] = [];
    for (let row = 0; row < ROWS; row++) {
      for (let col = 0; col < COLS; col++) {
        const seed = index * 11 + (row * COLS + col) * 7 + row * 5 + col * 3;
        const doorSign: 1 | -1 = slot.facesNorth || row === ROWS - 1 ? -1 : 1;
        const x = slot.x + (col - (COLS - 1) / 2) * m.colStep;
        const z = slot.z + (row - (ROWS - 1) / 2) * m.rowStep;
        const walkZ = z + doorSign * (m.cellD / 2 + STREET_D * 0.42);
        offices.push({ company: null, x, z, h: HEIGHTS[seed % HEIGHTS.length], walkX: x, walkZ, seed, row, doorSign });
      }
    }
    // The offices nearest the hub hold the linked companies
    [...offices]
      .sort((a, b) => Math.hypot(a.x, a.z) - Math.hypot(b.x, b.z))
      .forEach((office, k) => {
        office.company = block.offices[k] ?? null;
      });
    const labelX = slot.facesNorth ? slot.x : slot.x - Math.sign(slot.x) * (slot.w / 2);
    const labelZ = slot.facesNorth ? slot.z - slot.d / 2 : slot.z;
    return { block, slot, index, offices, labelX, labelZ };
  });
}

export type City = { group: THREE.Group; walkers: Walker[] };

type Glass = { dark: number; glow: number; strength: number; light: number; lightGlow: number; lightStrength: number };
const GLASS: Glass[] = [
  { dark: 0x6e76f0, glow: 0x3b44a8, strength: 0.38, light: 0x5a7896, lightGlow: 0x2c4866, lightStrength: 0.12 }, // sky indigo
  { dark: 0x5cc98f, glow: 0x287a52, strength: 0.34, light: 0x4c7c6e, lightGlow: 0x295247, lightStrength: 0.12 }, // emerald
  { dark: 0xe9b25c, glow: 0x9a6b12, strength: 0.36, light: 0x9a6b12, lightGlow: 0x704d0c, lightStrength: 0.14 }, // bronze
];
const WALLS: [number, number][] = [
  [0x1e2d56, 0xf2ece1], [0x27355e, 0xe4dac8], [0x1a2642, 0xd8cebc], [0x2c3454, 0xebe3d5], [0x23334e, 0xded2be],
];
const ROOFS: [number, number][] = [
  [0x151f38, 0xc8beac], [0x2b3c66, 0xb8ad9a], [0x1d3b3a, 0x8c6d46], [0x3b2d26, 0x6c7c78], [0x222c4a, 0xa89b85],
];

function std(dark: number, light: number | undefined, extra: THREE.MeshStandardMaterialParameters = {}) {
  const m = new THREE.MeshStandardMaterial({ color: dark, roughness: 0.6, ...extra });
  if (light !== undefined) m.userData.light = light;
  return m;
}

function glassMaterial(g: Glass) {
  const m = std(g.dark, g.light, { emissive: g.glow, emissiveIntensity: g.strength, roughness: 0.15, metalness: 0.3 });
  m.userData.lightEmissive = g.lightGlow;
  m.userData.lightEmissiveIntensity = g.lightStrength;
  return m;
}

function materials() {
  return {
    curb: std(0x1d2842, undefined, { roughness: 0.8 }),
    road: std(0x141b2d, undefined, { roughness: 0.88 }),
    marking: std(0xf4f1ea, undefined, { roughness: 0.6 }), // white in both themes
    bin: std(0x2a3557, 0x5f6878, { roughness: 0.5 }),
    binLid: std(0x5cc98f, undefined, { roughness: 0.4 }),
    trunk: std(0x5c4028, undefined, { roughness: 0.85 }),
    leaves: [std(0x28664b, undefined, { roughness: 0.75 }), std(0x3b855f, undefined, { roughness: 0.75 })],
    walls: WALLS.map(([dark, light]) => std(dark, light)),
    roofs: ROOFS.map(([dark, light]) => std(dark, light, { roughness: 0.5, metalness: 0.15 })),
    mullion: std(0x8f98ab, 0x6e5a3c, { roughness: 0.35, metalness: 0.45 }),
    glass: GLASS.map((g) => glassMaterial(g)),
    // construction sites
    dirt: std(0x3a2f24, 0xb59a74, { roughness: 0.95 }),
    concrete: std(0x4a5468, 0xb8b2a6, { roughness: 0.85 }),
    scaffold: std(0xd99a3a, 0xb07a20, { roughness: 0.4, metalness: 0.4 }),
    plank: std(0x6b5236, 0x9c7a4e, { roughness: 0.8 }),
    cone: std(0xf07c3c, undefined, { roughness: 0.5 }),
    crane: std(0xe9c23c, 0xc89a18, { roughness: 0.4, metalness: 0.35 }),
  };
}
type Materials = ReturnType<typeof materials>;

function adder(group: THREE.Group) {
  return (geometry: THREE.BufferGeometry, mat: THREE.Material, x: number, y: number, z: number) => {
    const mesh = new THREE.Mesh(geometry, mat);
    mesh.position.set(x, y, z);
    group.add(mesh);
    return mesh;
  };
}

/** A lot without a company: a dirt pad behind a fence, the first floors' concrete core in scaffolding, cones, a pile
 *  of materials and, on some lots, a tower crane. Still part of its block (a click opens the app). */
function buildSite(add: ReturnType<typeof adder>, w: number, d: number, h: number, seed: number, front: 1 | -1, mats: Materials): void {
  const hw = w / 2;
  const hd = d / 2;
  add(new THREE.BoxGeometry(w + 0.3, 0.06, d + 0.3), mats.dirt, 0, -0.06, 0);
  // The fence: posts every ~1 m with two rails, a gap on the street side for the trucks
  for (const s of [1, -1]) {
    for (let x = -hw; x <= hw + 0.01; x += w / Math.round(w)) add(new THREE.BoxGeometry(0.06, 0.6, 0.06), mats.mullion, x, 0.27, s * (hd + 0.1));
    for (let z = -hd; z <= hd + 0.01; z += d / Math.round(d)) add(new THREE.BoxGeometry(0.06, 0.6, 0.06), mats.mullion, s * (hw + 0.1), 0.27, z);
    for (const y of [0.2, 0.48]) {
      add(new THREE.BoxGeometry(0.04, 0.04, d + 0.2), mats.mullion, s * (hw + 0.1), y, 0);
      if (s !== front) add(new THREE.BoxGeometry(w + 0.2, 0.04, 0.04), mats.mullion, 0, y, s * (hd + 0.1));
      else for (const x of [-1, 1]) add(new THREE.BoxGeometry(w * 0.3, 0.04, 0.04), mats.mullion, x * (hw - w * 0.15 + 0.1), y, s * (hd + 0.1));
    }
  }
  // The concrete core, one to two floors up, in a scaffold of four poles and two plank decks
  const coreH = h * (seed % 2 === 0 ? 0.32 : 0.48);
  const cw = w * 0.62;
  const cd = d * 0.6;
  add(new THREE.BoxGeometry(cw, coreH, cd), mats.concrete, 0, coreH / 2 - 0.04, -front * d * 0.08);
  const poleH = coreH + 0.7;
  for (const sx of [1, -1]) {
    for (const sz of [1, -1]) add(new THREE.BoxGeometry(0.07, poleH, 0.07), mats.scaffold, sx * (cw / 2 + 0.2), poleH / 2 - 0.04, -front * d * 0.08 + sz * (cd / 2 + 0.2));
  }
  for (const y of [coreH * 0.5, coreH + 0.3]) {
    add(new THREE.BoxGeometry(cw + 0.5, 0.05, 0.3), mats.plank, 0, y, -front * d * 0.08 + front * (cd / 2 + 0.2));
  }
  // Cones at the gate and a pile of materials beside it
  for (const x of [-w * 0.18, w * 0.18]) add(new THREE.ConeGeometry(0.1, 0.28, 10), mats.cone, x, 0.11, front * (hd - 0.15));
  add(new THREE.BoxGeometry(0.7, 0.18, 0.4), mats.plank, -hw * 0.62, 0.06, front * hd * 0.55);
  add(new THREE.BoxGeometry(0.5, 0.16, 0.36), mats.concrete, -hw * 0.6, 0.23, front * hd * 0.55);
  // A tower crane on every third lot: mast, jib, counterweight
  if (seed % 3 === 0) {
    const mastH = h + 1.6;
    const mx = hw * 0.62;
    const mz = -front * hd * 0.6;
    add(new THREE.BoxGeometry(0.16, mastH, 0.16), mats.crane, mx, mastH / 2 - 0.04, mz);
    add(new THREE.BoxGeometry(w * 1.05, 0.1, 0.12), mats.crane, mx - w * 0.38, mastH, mz);
    add(new THREE.BoxGeometry(0.34, 0.24, 0.24), mats.concrete, mx + 0.45, mastH - 0.12, mz);
    add(new THREE.BoxGeometry(0.02, 0.9, 0.02), mats.mullion, mx - w * 0.7, mastH - 0.45, mz);
  }
}

/** One office: its plot, one of six building styles, one of three doors and its roof beacon (a lot without a
 *  company is a construction site instead). */
function buildOffice(office: PlacedOffice, block: PlacedBlock, mats: Materials, accent: THREE.Material): THREE.Group {
  const g = new THREE.Group();
  const add = adder(g);
  const m = metrics(block.slot);
  const { seed, h, doorSign } = office;
  const lit = office.company !== null;
  const archetype = seed % 6;
  const wall = mats.walls[seed % mats.walls.length];
  const wall2 = mats.walls[(seed + 2) % mats.walls.length];
  const roof = mats.roofs[(seed + 1) % mats.roofs.length];
  const glass = mats.glass[(seed + block.index) % GLASS.length];
  const w = (m.cellW - 0.54) * (archetype === 2 ? 0.96 : 1);
  const d = (m.cellD - 0.62) * (archetype === 2 ? 0.96 : 1);
  const hw = w / 2;
  const hd = d / 2;

  add(new THREE.BoxGeometry(m.cellW - 0.12, 0.14, m.cellD - 0.12), mats.curb, 0, -0.16, 0);

  if (!lit) {
    buildSite(add, w, d, h, seed, doorSign, mats);
  } else if (archetype === 0) {
    // Curtain-wall glass high-rise: mullions, cornice, helipad, spire
    add(new THREE.BoxGeometry(w, h, d), wall, 0, h / 2 - 0.08, 0);
    for (const s of [1, -1]) add(new THREE.BoxGeometry(w * 0.86, h * 0.76, 0.05), glass, 0, h * 0.54, s * (hd + 0.01));
    for (const s of [1, -1]) add(new THREE.BoxGeometry(0.05, h * 0.76, d * 0.84), glass, s * (hw + 0.01), h * 0.54, 0);
    for (const fx of [-0.3, 0, 0.3]) {
      for (const s of [1, -1]) add(new THREE.BoxGeometry(0.08, h * 0.78, 0.08), mats.mullion, w * fx, h * 0.54, s * (hd + 0.02));
    }
    add(new THREE.BoxGeometry(w + 0.24, 0.18, d + 0.24), roof, 0, h - 0.02, 0);
    add(new THREE.CylinderGeometry(w * 0.34, w * 0.36, 0.12, 20), wall2, 0, h + 0.12, 0);
    add(new THREE.CylinderGeometry(0.04, 0.09, 1.15, 8), mats.mullion, w * 0.25, h + 0.65, -d * 0.2);
  } else if (archetype === 1) {
    // Stepped setback tower: podium, ledge, upper tower, window columns, hip roof
    const lowerH = h * 0.56;
    const upperH = h * 0.48;
    const uw = w * 0.74;
    const ud = d * 0.74;
    add(new THREE.BoxGeometry(w, lowerH, d), wall, 0, lowerH / 2 - 0.08, 0);
    add(new THREE.BoxGeometry(w + 0.2, 0.14, d + 0.2), roof, 0, lowerH - 0.06, 0);
    add(new THREE.BoxGeometry(uw, upperH, ud), wall2, 0, lowerH + upperH / 2 - 0.06, 0);
    for (const fx of [-0.28, 0, 0.28]) {
      for (const s of [1, -1]) {
        add(new THREE.BoxGeometry(w * 0.18, lowerH * 0.55, 0.06), glass, w * fx, lowerH * 0.55, s * (hd + 0.01));
        add(new THREE.BoxGeometry(uw * 0.18, upperH * 0.62, 0.06), glass, uw * fx, lowerH + upperH * 0.48, s * (ud / 2 + 0.01));
      }
    }
    const hip = add(new THREE.ConeGeometry(Math.min(uw, ud) * 0.64, 0.95, 4), roof, 0, lowerH + upperH + 0.42, 0);
    hip.rotation.y = Math.PI / 4;
  } else if (archetype === 2) {
    // Twin towers with a glass atrium and mono-pitch roofs
    const wingW = w * 0.4;
    const heights = [h, h * 0.82];
    [-1, 1].forEach((s, k) => {
      add(new THREE.BoxGeometry(wingW, heights[k], d), k === 0 ? wall : wall2, s * w * 0.28, heights[k] / 2 - 0.08, 0);
      for (const fy of [0.35, 0.62, 0.82]) {
        add(new THREE.BoxGeometry(wingW + 0.05, 0.26, d * 0.86), glass, s * w * 0.28, heights[k] * fy, 0);
      }
      const slope = add(new THREE.BoxGeometry(wingW + 0.16, 0.16, d + 0.16), roof, s * w * 0.28, heights[k], 0);
      slope.rotation.z = -s * 0.12;
    });
    const atriumH = Math.min(...heights) * 0.88;
    add(new THREE.BoxGeometry(w * 0.26, atriumH, d * 0.84), glass, 0, atriumH / 2 - 0.08, 0);
  } else if (archetype === 3) {
    // Brutalist tech hub: grid windows, parapet, roof garden with a tree
    add(new THREE.BoxGeometry(w, h, d), wall2, 0, h / 2 - 0.08, 0);
    for (let floor = 0; floor < 3; floor++) {
      const y = 0.95 + floor * ((h - 1.1) / 3);
      for (const fx of [-0.3, 0, 0.3]) {
        for (const s of [1, -1]) add(new THREE.BoxGeometry(w * 0.21, 0.42, 0.06), glass, w * fx, y, s * (hd + 0.01));
      }
    }
    add(new THREE.BoxGeometry(w + 0.18, 0.24, d + 0.18), roof, 0, h, 0);
    add(new THREE.BoxGeometry(w * 0.78, 0.1, d * 0.78), mats.leaves[0], 0, h + 0.14, 0);
    add(new THREE.DodecahedronGeometry(0.48, 1), mats.leaves[1], -w * 0.2, h + 0.55, d * 0.15);
  } else if (archetype === 4) {
    // Terraced sunshade tower: glass bands, ledges, a glass barrel vault
    add(new THREE.BoxGeometry(w * 0.92, h, d * 0.92), wall, 0, h / 2 - 0.08, 0);
    for (const fy of [0.34, 0.58, 0.82]) {
      add(new THREE.BoxGeometry(w * 0.94, 0.36, d * 0.94), glass, 0, h * fy, 0);
      add(new THREE.BoxGeometry(w + 0.28, 0.1, d + 0.28), roof, 0, h * fy + 0.22, 0);
    }
    const vault = add(new THREE.CylinderGeometry(w * 0.34, w * 0.34, d * 0.72, 16, 1, false, 0, Math.PI), glass, 0, h + 0.04, 0);
    vault.rotation.set(0, Math.PI / 2, Math.PI / 2);
  } else {
    // Flagship hall: vertical glass strips on all sides, a gabled roof
    add(new THREE.BoxGeometry(w, h, d), wall, 0, h / 2 - 0.08, 0);
    for (const fx of [-0.32, -0.11, 0.11, 0.32]) {
      for (const s of [1, -1]) add(new THREE.BoxGeometry(0.28, h * 0.72, 0.06), glass, w * fx, h * 0.54, s * (hd + 0.01));
    }
    for (const fz of [-0.28, 0, 0.28]) {
      for (const s of [1, -1]) add(new THREE.BoxGeometry(0.06, h * 0.72, 0.34), glass, s * (hw + 0.01), h * 0.54, d * fz);
    }
    const ridge = add(new THREE.CylinderGeometry(w * 0.52, w * 0.52, d + 0.2, 3), roof, 0, h + 0.22, 0);
    ridge.rotation.x = Math.PI / 2;
    ridge.scale.set(1, 0.42, 1);
  }

  if (lit) {
    // The door, on the side facing its street
    const front = (out: number) => doorSign * (hd + out);
    const doorStyle = seed % 3;
    if (doorStyle === 0) {
      // Double glass doors under a canopy
      add(new THREE.BoxGeometry(1.36, 1.02, 0.06), accent, 0, 0.42, front(0.01));
      for (const x of [-0.3, 0.3]) add(new THREE.BoxGeometry(0.54, 0.92, 0.08), glass, x, 0.38, front(0.02));
      add(new THREE.BoxGeometry(1.85, 0.1, 0.62), roof, 0, 0.96, front(0.24));
    } else if (doorStyle === 1) {
      // Revolving-door rotunda
      add(new THREE.CylinderGeometry(0.68, 0.68, 0.98, 16), glass, 0, 0.41, front(0.18));
      add(new THREE.CylinderGeometry(0.76, 0.76, 0.12, 16), accent, 0, 0.94, front(0.18));
    } else {
      // Portal with two columns and a pediment
      add(new THREE.BoxGeometry(1.05, 0.96, 0.08), accent, 0, 0.4, front(0.02));
      for (const x of [-0.72, 0.72]) add(new THREE.CylinderGeometry(0.1, 0.12, 1.08, 10), mats.mullion, x, 0.46, front(0.18));
      add(new THREE.BoxGeometry(1.75, 0.18, 0.48), roof, 0, 1.04, front(0.16));
    }
    add(new THREE.OctahedronGeometry(0.24, 0), accent, 0, h + 0.88, 0); // the company's roof beacon
  }
  if (office.row === 1 && Math.round((office.x - block.slot.x) / m.colStep) % 2 === 0) {
    add(new THREE.CylinderGeometry(0.12, 0.1, 0.34, 8), mats.bin, hw + 0.18, 0.06, hd - 0.25);
    add(new THREE.CylinderGeometry(0.125, 0.125, 0.06, 8), mats.binLid, hw + 0.18, 0.25, hd - 0.25);
  }
  g.position.set(office.x - block.slot.x, 0, office.z - block.slot.z);
  if (office.company) {
    const companyId = office.company.companyId;
    g.traverse((child) => {
      child.userData.companyId = companyId;
    });
  }
  return g;
}

/** Streets, trees, offices and the app engineer of one block. */
function buildBlock(block: PlacedBlock, mats: Materials, walkers: Walker[]): THREE.Group {
  const g = new THREE.Group();
  const add = adder(g);
  const { slot } = block;
  const m = metrics(slot);
  g.position.set(slot.x, 0, slot.z);
  const accent = std(slot.accent, undefined, { emissive: slot.accent, emissiveIntensity: 0.55, roughness: 0.25 });

  add(new THREE.BoxGeometry(slot.w, 0.28, slot.d), mats.curb, 0, -0.36, 0); // the block's sidewalk pad
  const streetZ = Array.from({ length: ROWS - 1 }, (_, r) => (r - (ROWS - 2) / 2) * m.rowStep);
  const streetX = Array.from({ length: COLS - 1 }, (_, c) => (c - (COLS - 2) / 2) * m.colStep);
  for (const z of streetZ) add(new THREE.BoxGeometry(slot.w - 0.3, 0.08, STREET_D), mats.road, 0, -0.2, z);
  for (const x of streetX) add(new THREE.BoxGeometry(STREET_W, 0.08, slot.d - 0.3), mats.road, x, -0.2, 0);
  // A broken white line down the middle of each inner street, clear of the junctions
  const dashes: Place[] = [];
  for (const z of streetZ) {
    for (let x = -slot.w / 2 + 1; x <= slot.w / 2 - 1; x += 1.6) {
      if (streetX.every((sx) => Math.abs(x - sx) > STREET_W / 2 + 0.5)) dashes.push({ x, y: -0.155, z });
    }
  }
  for (const x of streetX) {
    for (let z = -slot.d / 2 + 1; z <= slot.d / 2 - 1; z += 1.6) {
      if (streetZ.every((sz) => Math.abs(z - sz) > STREET_D / 2 + 0.5)) dashes.push({ x, y: -0.15, z, ry: Math.PI / 2 });
    }
  }
  g.add(instanced(new THREE.BoxGeometry(0.8, 0.01, 0.07), mats.marking, dashes));

  // Trees where the inner streets cross (never on the outer sides)
  streetZ.forEach((z, r) =>
    streetX.forEach((x, c) => {
      const tree = new THREE.Group();
      const addTree = adder(tree);
      const [a, b] = (r + c) % 2 === 0 ? mats.leaves : [mats.leaves[1], mats.leaves[0]];
      addTree(new THREE.CylinderGeometry(0.38, 0.42, 0.16, 10), mats.curb, 0, 0.08, 0);
      addTree(new THREE.CylinderGeometry(0.11, 0.16, 0.78, 8), mats.trunk, 0, 0.42, 0);
      addTree(new THREE.DodecahedronGeometry(0.62, 1), a, 0, 1.15, 0);
      addTree(new THREE.DodecahedronGeometry(0.45, 1), b, 0.18, 1.48, 0.12);
      tree.position.set(x, -0.18, z);
      g.add(tree);
    }),
  );

  for (const office of block.offices) g.add(buildOffice(office, block, mats, accent));

  // The app engineer walks the street between the second and third rows
  walkers.push(
    ...buildWalkers(g, [
      {
        name: `${block.block.name} · engineer`,
        a: [-m.colStep * 1.6, streetZ[streetZ.length - 1]],
        b: [m.colStep * 1.6, streetZ[streetZ.length - 1]],
        speed: 1.1,
        jacket: slot.accent,
        hair: 0x0a1128,
        phase: block.index * 1.3,
        y: -0.16,
      },
    ]),
  );

  const appId = block.block.appId;
  g.traverse((child) => {
    child.userData.appId = appId;
  });
  return g;
}

/** Build every block (the theme is applied afterwards by the caller, like the rest of the scene). */
export function buildCity(scene: THREE.Scene, blocks: CityBlock[]): City {
  const group = new THREE.Group();
  const walkers: Walker[] = [];
  const mats = materials();
  const placed = layoutCity(blocks);
  for (const block of placed) group.add(buildBlock(block, mats, walkers));
  // the lots no app uses yet are parks (parks.ts) until an app takes them
  SLOTS.slice(placed.length).forEach((slot, i) => group.add(buildLotPark(slot.x, slot.z, slot.w, slot.d, placed.length + i, walkers)));
  scene.add(group);
  return { group, walkers };
}

/** Take the city out of the scene and free its GPU memory (before building it again with new data). */
export function disposeCity(scene: THREE.Scene, city: City): void {
  scene.remove(city.group);
  const materials = new Set<THREE.Material>();
  city.group.traverse((object) => {
    if (object instanceof THREE.Mesh) {
      object.geometry.dispose();
      for (const m of Array.isArray(object.material) ? object.material : [object.material]) materials.add(m);
    }
  });
  for (const m of materials) m.dispose();
}

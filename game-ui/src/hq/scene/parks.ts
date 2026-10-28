import * as THREE from "three";

import { instanced, type Place } from "@/hq/scene/instanced";
import { buildWalkers, type Walker, type WalkerSpec } from "@/hq/scene/staff";

// The open ground around the city (Vince, 2026-10-28): a long park north of the flyover (a path, a fountain plaza,
// benches, flower beds, lamps, trees and bushes), a park south of the south blocks (a path, a pond, a gazebo), rows of
// trees on the far west and east, and a park on every city lot no app uses yet (buildLotPark, called by city.ts).
// Pedestrians walk the sidewalks and the park paths. Decoration only: nothing here is clickable. Built in dark colors
// with light partners (palette.ts), like the rest of the scene.

const GROUND = -0.4; // the outer parks' path height (the grass is at -0.55)
const LOT_GROUND = -0.2; // a lot park's path height (the lots' pads are at -0.22)
const SIDEWALK = -0.3; // the top of the road sidewalks (environment.ts)

const NORTH = { z: -38.5, x0: -54, x1: 54, z0: -31, z1: -46 }; // behind the flyover (z -29.6)
const SOUTH = { z: 55.5, x0: -56, x1: 56, z0: 52.5, z1: 66 }; // behind the south blocks (z 50.5)
const NORTH_BENCHES = [-44, -24, -12, 12, 24, 44];
const SOUTH_BENCHES = [-40, -12, 12, 40];

const FLOWERS = [0xf07c7c, 0xe9b25c, 0xf4f1ea, 0x6e76f0];
const JACKETS = [0x5cc98f, 0xf07c7c, 0xe9b25c, 0x6e76f0, 0xf4f1ea, 0x9a6b12];
const HAIR = [0x1a202c, 0x4a3525, 0x0a1128, 0x2d3748];

// Walkers on the roads' sidewalks (3.55 m from the road's center, clear of the street lights at the curb and of the
// corners) and on the park paths. Slow: a walker covers its path in about 14 s.
const PEDESTRIANS: WalkerSpec[] = [
  { name: "pedestrian", a: [-13, -21.75], b: [-4, -21.75], speed: 0.55, jacket: 0x5cc98f, hair: 0x1a202c, phase: 0.3, y: SIDEWALK },
  { name: "pedestrian", a: [4, -14.65], b: [13, -14.65], speed: 0.5, jacket: 0xf07c7c, hair: 0x4a3525, phase: 1.7, y: SIDEWALK },
  { name: "pedestrian", a: [-12, 14.65], b: [-3, 14.65], speed: 0.55, jacket: 0xe9b25c, hair: 0x0a1128, phase: 2.9, y: SIDEWALK },
  { name: "pedestrian", a: [24, 21.75], b: [36, 21.75], speed: 0.45, jacket: 0x6e76f0, hair: 0x2d3748, phase: 0.9, y: SIDEWALK },
  { name: "pedestrian", a: [-14.65, -12], b: [-14.65, -2], speed: 0.5, jacket: 0xf4f1ea, hair: 0x1a202c, phase: 4.1, y: SIDEWALK },
  { name: "pedestrian", a: [21.75, -12], b: [21.75, 0], speed: 0.45, jacket: 0x9a6b12, hair: 0x4a3525, phase: 2.2, y: SIDEWALK },
  { name: "pedestrian", a: [-21.75, 26], b: [-21.75, 38], speed: 0.45, jacket: 0x5cc98f, hair: 0x2d3748, phase: 5.0, y: SIDEWALK },
  { name: "pedestrian", a: [-26, NORTH.z], b: [-12, NORTH.z], speed: 0.4, jacket: 0x6e76f0, hair: 0x0a1128, phase: 1.1, y: GROUND },
  { name: "pedestrian", a: [12, NORTH.z], b: [26, NORTH.z], speed: 0.4, jacket: 0xf07c7c, hair: 0x1a202c, phase: 3.6, y: GROUND },
  { name: "pedestrian", a: [32, -44], b: [32, -33], speed: 0.45, jacket: 0xe9b25c, hair: 0x4a3525, phase: 0.5, y: GROUND },
  { name: "pedestrian", a: [-20, SOUTH.z], b: [-8, SOUTH.z], speed: 0.45, jacket: 0xf4f1ea, hair: 0x2d3748, phase: 2.6, y: GROUND },
  { name: "pedestrian", a: [10, SOUTH.z], b: [22, SOUTH.z], speed: 0.45, jacket: 0x5cc98f, hair: 0x0a1128, phase: 4.4, y: GROUND },
];

function std(dark: number, light?: number, extra: THREE.MeshStandardMaterialParameters = {}) {
  const m = new THREE.MeshStandardMaterial({ color: dark, roughness: 0.7, ...extra });
  if (light !== undefined) m.userData.light = light;
  return m;
}

/** One set of park materials (a lot park gets its own: the city frees its materials when it is rebuilt). */
function materials() {
  const water = std(0x2c5a8a, 0x7fb3d9, { roughness: 0.1, metalness: 0.2, emissive: 0x16304d, emissiveIntensity: 0.4 });
  water.userData.lightEmissive = 0x5c8fb8;
  water.userData.lightEmissiveIntensity = 0.15;
  return {
    lawn: std(0x16382c, undefined, { roughness: 0.85 }),
    path: std(0x1d2842, undefined, { roughness: 0.8 }),
    stone: std(0x4a5468, 0xb8b2a6, { roughness: 0.6 }),
    water,
    soil: std(0x3a2f24, 0xb59a74, { roughness: 0.95 }),
    wood: std(0x6b5236, 0x9c7a4e, { roughness: 0.8 }),
    metal: std(0x2a3557, 0x5f6878, { roughness: 0.5 }),
    trunk: std(0x5c4028, undefined, { roughness: 0.85 }),
    leaves: [std(0x28664b, undefined, { roughness: 0.75 }), std(0x3b855f, undefined, { roughness: 0.75 })],
    roof: std(0x2b3c66, 0xb8ad9a, { roughness: 0.5 }),
    flowers: FLOWERS.map((color) => std(color, undefined, { roughness: 0.5 })),
  };
}
type Materials = ReturnType<typeof materials>;

function box(w: number, h: number, d: number, mat: THREE.Material, x: number, y: number, z: number) {
  const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mat);
  m.position.set(x, y, z);
  m.receiveShadow = true;
  return m;
}

function cylinder(rTop: number, rBottom: number, h: number, mat: THREE.Material, x: number, y: number, z: number) {
  const m = new THREE.Mesh(new THREE.CylinderGeometry(rTop, rBottom, h, 24), mat);
  m.position.set(x, y, z);
  m.receiveShadow = true;
  return m;
}

/** A round plaza with a two-tier fountain; y = the path height. */
function fountain(g: THREE.Group, mats: Materials, x: number, y: number, z: number): void {
  g.add(cylinder(3.2, 3.2, 0.04, mats.path, x, y + 0.005, z));
  g.add(cylinder(1.7, 1.8, 0.45, mats.stone, x, y + 0.2, z));
  g.add(cylinder(1.5, 1.5, 0.05, mats.water, x, y + 0.4, z));
  g.add(cylinder(0.18, 0.25, 1.1, mats.stone, x, y + 0.7, z));
  g.add(cylinder(0.6, 0.3, 0.18, mats.stone, x, y + 1.3, z));
  const spout = new THREE.Mesh(new THREE.SphereGeometry(0.25, 16, 12), mats.water);
  spout.position.set(x, y + 1.45, z);
  g.add(spout);
}

/** Benches on both sides of a path (along x: z = the path; along z: x = the path), backs away from the path. */
function benchesBy(path: "x" | "z", at: number, spots: number[], y: number): Place[] {
  return spots.flatMap((p) =>
    path === "x"
      ? [{ x: p, y, z: at + 1.35 }, { x: p, y, z: at - 1.35, ry: Math.PI }]
      : [{ x: at + 1.35, y, z: p, ry: Math.PI / 2 }, { x: at - 1.35, y, z: p, ry: -Math.PI / 2 }],
  );
}

function addBenches(g: THREE.Group, mats: Materials, benches: Place[]): void {
  const seats = benches.map((b) => ({ ...b, y: b.y + 0.4 }));
  g.add(instanced(new THREE.BoxGeometry(1.1, 0.08, 0.38), mats.wood, seats));
  g.add(instanced(new THREE.BoxGeometry(1.1, 0.32, 0.06).translate(0, 0.2, 0.17), mats.wood, seats));
  for (const lx of [-0.45, 0.45]) g.add(instanced(new THREE.BoxGeometry(0.06, 0.4, 0.32).translate(lx, -0.2, 0), mats.metal, seats));
}

/** Round flower beds: soil and a ring of flowers in four colors. */
function addBeds(g: THREE.Group, mats: Materials, beds: [number, number][], y: number): void {
  g.add(instanced(new THREE.CylinderGeometry(0.95, 1, 0.18, 16), mats.soil, beds.map(([x, z]) => ({ x, y: y + 0.02, z }))));
  const blooms: Place[][] = FLOWERS.map(() => []);
  beds.forEach(([x, z], b) => {
    for (let k = 0; k < 8; k++) {
      const a = (k / 8) * Math.PI * 2 + b;
      const r = k % 2 ? 0.62 : 0.3;
      blooms[(k + b) % FLOWERS.length].push({ x: x + Math.cos(a) * r, y: y + 0.2, z: z + Math.sin(a) * r });
    }
  });
  const bloomShape = new THREE.SphereGeometry(0.13, 8, 6);
  mats.flowers.forEach((m, i) => g.add(instanced(bloomShape, m, blooms[i])));
}

/** Low-poly trees (a trunk and two cones), sizes varied by their order. */
function addTrees(g: THREE.Group, mats: Materials, trees: Place[]): void {
  trees.forEach((t, i) => {
    const s = 0.85 + (i % 3) * 0.2;
    t.s = [s, s, s];
    t.ry = i;
  });
  g.add(instanced(new THREE.CylinderGeometry(0.14, 0.22, 0.9, 8).translate(0, 0.45, 0), mats.trunk, trees));
  const lower = new THREE.ConeGeometry(0.85, 1.5, 7).translate(0, 1.35, 0);
  const upper = new THREE.ConeGeometry(0.62, 1.2, 7).translate(0, 2.05, 0);
  [0, 1].forEach((k) => {
    const mine = trees.filter((_, i) => i % 2 === k);
    g.add(instanced(lower, mats.leaves[k], mine), instanced(upper, mats.leaves[1 - k], mine));
  });
}

function addBushes(g: THREE.Group, mats: Materials, bushes: Place[]): void {
  bushes.forEach((b, i) => {
    b.ry = i;
    b.s = [1, 0.72, 1];
  });
  const shape = new THREE.DodecahedronGeometry(0.42, 0);
  g.add(instanced(shape, mats.leaves[0], bushes.filter((_, i) => i % 2 === 0)));
  g.add(instanced(shape, mats.leaves[1], bushes.filter((_, i) => i % 2 === 1)));
}

export type Parks = { walkers: Walker[] };

/** The parks outside the city and the pedestrians on the sidewalks; their lamps share the street lights' material. */
export function buildParks(env: THREE.Group, lamp: THREE.Material): Parks {
  const mats = materials();

  // Lawns and paths
  for (const p of [NORTH, SOUTH]) {
    const w = p.x1 - p.x0;
    const d = Math.abs(p.z1 - p.z0);
    env.add(box(w, 0.12, d, mats.lawn, (p.x0 + p.x1) / 2, -0.5, (p.z0 + p.z1) / 2));
    env.add(box(w - 4, 0.04, 1.6, mats.path, (p.x0 + p.x1) / 2, GROUND - 0.02, p.z));
  }
  for (const x of [-32, 32]) env.add(box(1.4, 0.04, 15, mats.path, x, GROUND - 0.02, NORTH.z));
  fountain(env, mats, 0, GROUND, NORTH.z);

  // South: a pond ringed with stones, and a gazebo
  const pond = cylinder(2.8, 2.8, 0.05, mats.water, -30, GROUND - 0.01, 60.5);
  pond.scale.set(1.5, 1, 1);
  env.add(pond);
  const rocks: Place[] = Array.from({ length: 14 }, (_, i) => {
    const a = (i / 14) * Math.PI * 2;
    return { x: -30 + Math.cos(a) * 4.3, y: GROUND + 0.05, z: 60.5 + Math.sin(a) * 2.95, ry: i, s: [1 + (i % 3) * 0.25, 0.7, 1] };
  });
  env.add(instanced(new THREE.DodecahedronGeometry(0.3, 0), mats.stone, rocks));
  env.add(cylinder(2.4, 2.5, 0.2, mats.stone, 30, GROUND + 0.08, 60.5));
  const posts: Place[] = Array.from({ length: 6 }, (_, i) => {
    const a = (i / 6) * Math.PI * 2;
    return { x: 30 + Math.cos(a) * 2.1, y: GROUND + 1.1, z: 60.5 + Math.sin(a) * 2.1 };
  });
  env.add(instanced(new THREE.CylinderGeometry(0.08, 0.08, 1.9, 8), mats.wood, posts));
  const gazeboRoof = new THREE.Mesh(new THREE.ConeGeometry(2.9, 1.2, 6), mats.roof);
  gazeboRoof.position.set(30, GROUND + 2.6, 60.5);
  gazeboRoof.castShadow = true;
  env.add(gazeboRoof);

  addBenches(env, mats, [...benchesBy("x", NORTH.z, NORTH_BENCHES, GROUND), ...benchesBy("x", SOUTH.z, SOUTH_BENCHES, GROUND)]);
  addBeds(
    env,
    mats,
    [
      [-4.5, -34.5], [4.5, -34.5], [-4.5, -42.5], [4.5, -42.5],
      [-17.5, -34.8], [17.5, -34.8], [-17.5, -42.2], [17.5, -42.2],
      [-38.5, -34.8], [38.5, -34.8], [-38.5, -42.2], [38.5, -42.2],
      [-20, 59.5], [0, 59.5], [20, 59.5], [-45, 59.5], [45, 59.5],
    ],
    GROUND,
  );

  // Park lamps along the paths: they light up with the street lights (the same material)
  const lamps: Place[] = [
    ...[-50, -36, -18, -6, 6, 18, 36, 50].map((x, i) => ({ x, y: GROUND, z: NORTH.z + (i % 2 ? 0.95 : -0.95) })),
    ...[-48, -24, 0, 24, 48].map((x, i) => ({ x, y: GROUND, z: SOUTH.z + (i % 2 ? 0.95 : -0.95) })),
  ];
  env.add(instanced(new THREE.CylinderGeometry(0.04, 0.05, 1.6, 8).translate(0, 0.8, 0), mats.metal, lamps));
  env.add(instanced(new THREE.SphereGeometry(0.14, 12, 8).translate(0, 1.65, 0), lamp, lamps));

  // Trees: two rows in the north park, rows in the south park, and lines on the far west and east
  const trees: Place[] = [];
  for (let x = -49; x <= 49; x += 7) {
    for (const z of [-33.2, -43.8]) if (Math.abs(Math.abs(x) - 32) >= 1.5) trees.push({ x, y: -0.5, z }); // not on the cross paths
  }
  for (let x = -52; x <= 52; x += 8) {
    trees.push({ x, y: -0.5, z: 64 });
    if (Math.abs(x + 30) > 6 && Math.abs(x - 30) > 5) trees.push({ x: x + 4, y: -0.5, z: 53.2 }); // clear of the pond and gazebo
  }
  for (let z = -10; z <= 46; z += 7) for (const x of [-61, 61]) trees.push({ x, y: -0.5, z });
  addTrees(env, mats, trees);

  // Bushes along the park paths, clear of the benches, cross paths and the plaza
  const bushes: Place[] = [];
  for (let x = -50; x <= 50; x += 3.5) {
    if (Math.abs(x) < 4.5 || Math.abs(Math.abs(x) - 32) < 1.5 || NORTH_BENCHES.some((b) => Math.abs(x - b) < 1.2)) continue;
    bushes.push({ x, y: GROUND, z: NORTH.z + 2.3 }, { x: x + 1.7, y: GROUND, z: NORTH.z - 2.3 });
  }
  for (let x = -52; x <= 52; x += 4) {
    if (!SOUTH_BENCHES.some((b) => Math.abs(x - b) < 1.3)) bushes.push({ x, y: GROUND, z: SOUTH.z - 2.0 });
  }
  addBushes(env, mats, bushes);

  return { walkers: buildWalkers(env, PEDESTRIANS) };
}

/**
 * A park on a city lot no app uses yet, w × d around (x, z): two crossing paths with a fountain plaza in the middle,
 * trees, a flower bed, benches and bushes in each quarter, and three people walking. When an app takes the lot, the
 * city is rebuilt and its block stands here instead.
 */
export function buildLotPark(x: number, z: number, w: number, d: number, seed: number, walkers: Walker[]): THREE.Group {
  const g = new THREE.Group();
  g.position.set(x, 0, z);
  const mats = materials();
  const hw = w / 2;
  const hd = d / 2;

  g.add(box(w, 0.28, d, mats.lawn, 0, -0.36, 0));
  g.add(box(w - 1, 0.04, 1.6, mats.path, 0, LOT_GROUND - 0.02, 0), box(1.6, 0.04, d - 1, mats.path, 0, LOT_GROUND - 0.02, 0));
  fountain(g, mats, 0, LOT_GROUND, 0);

  const xBenches = [-0.62, -0.3, 0.3, 0.62].map((f) => f * hw);
  const zBenches = [-0.6, 0.6].map((f) => f * hd);
  addBenches(g, mats, [...benchesBy("x", 0, xBenches, LOT_GROUND), ...benchesBy("z", 0, zBenches, LOT_GROUND)]);

  const trees: Place[] = [];
  const beds: [number, number][] = [];
  for (const sx of [1, -1]) {
    for (const sz of [1, -1]) {
      for (const fx of [0.3, 0.6, 0.88]) for (const fz of [0.35, 0.8]) trees.push({ x: sx * fx * hw, y: -0.22, z: sz * fz * hd });
      beds.push([sx * 0.45 * hw, sz * 0.58 * hd]);
    }
  }
  addTrees(g, mats, trees);
  addBeds(g, mats, beds, LOT_GROUND);

  const bushes: Place[] = [];
  for (let p = 4.5; p < hw - 1; p += 2.6) {
    if (xBenches.some((b) => Math.abs(Math.abs(b) - p) < 1)) continue;
    for (const s of [1, -1]) bushes.push({ x: s * p, y: LOT_GROUND, z: 1.9 }, { x: s * p, y: LOT_GROUND, z: -1.9 });
  }
  for (let p = 4.5; p < hd - 1; p += 2.6) {
    if (zBenches.some((b) => Math.abs(Math.abs(b) - p) < 1)) continue;
    for (const s of [1, -1]) bushes.push({ x: 1.9, y: LOT_GROUND, z: s * p }, { x: -1.9, y: LOT_GROUND, z: s * p });
  }
  addBushes(g, mats, bushes);

  const paths: WalkerSpec[] = [
    { name: "pedestrian", a: [-hw + 1.5, 0.35], b: [-4.2, 0.35], speed: 0.5, jacket: 0, hair: 0, phase: seed, y: LOT_GROUND },
    { name: "pedestrian", a: [4.2, -0.35], b: [hw - 1.5, -0.35], speed: 0.45, jacket: 0, hair: 0, phase: seed + 2, y: LOT_GROUND },
    { name: "pedestrian", a: [0.35, 4.2], b: [0.35, hd - 1.5], speed: 0.5, jacket: 0, hair: 0, phase: seed + 4, y: LOT_GROUND },
  ];
  const people = paths.map((p, i) => ({ ...p, jacket: JACKETS[(seed + i) % JACKETS.length], hair: HAIR[(seed + i) % HAIR.length] }));
  walkers.push(...buildWalkers(g, people));
  return g;
}

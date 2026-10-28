import * as THREE from "three";

// What surrounds the HQ: a park with lawns and trees, four roads with raised sidewalks, zebra crossings, street lights
// (lit at night by the PHT clock) and a traffic light on every corner of the four crossings, bushes along the way, a
// flyover in the north and a few cars driving around. No lines down the middle of the roads (Vince, 2026-10-28).
// Decoration only: nothing here is clickable. Small repeated parts are instanced meshes (one draw call per kind).

type Car = { mesh: THREE.Group; axis: "x" | "z"; dir: 1 | -1; speed: number };

type Signal = Record<"red" | "amber" | "green", THREE.MeshStandardMaterial>;

export type Environment = {
  cars: Car[];
  signals: [Signal, Signal]; // [0] the lights facing the east-west roads, [1] the north-south ones
  signalTime: number;
  lamp: THREE.MeshStandardMaterial; // the street lights' heads
};

const LANES: { axis: "x" | "z"; fixed: number; y: number; dir: 1 | -1; speed: number; start: number }[] = [
  { axis: "x", fixed: -19.4, y: -0.22, dir: 1, speed: 7.5, start: -28 },
  { axis: "x", fixed: -17.0, y: -0.22, dir: -1, speed: 6.8, start: 22 },
  { axis: "x", fixed: 17.0, y: -0.22, dir: 1, speed: 6.4, start: -14 },
  { axis: "x", fixed: 19.4, y: -0.22, dir: -1, speed: 8.1, start: 30 },
  { axis: "z", fixed: -19.4, y: -0.21, dir: 1, speed: 7.0, start: -20 },
  { axis: "z", fixed: 19.4, y: -0.21, dir: -1, speed: 7.4, start: 18 },
  { axis: "x", fixed: -27.5, y: 3.85, dir: 1, speed: 10.5, start: -35 }, // on the flyover
];

const TREES: [number, number][] = [
  [-13.5, -13.5], [-8.5, -13.6], [8.5, -13.6], [13.5, -13.5],
  [-13.5, 13.5], [-8.5, 13.6], [8.5, 13.6], [13.5, 13.5],
  [-13.6, -8.5], [-13.6, 8.5], [13.6, -8.5], [13.6, 8.5],
  [-23.5, -23.5], [23.5, -23.5], [-11.0, -23.0], [11.0, -23.0],
  // V4: the 8 park trees west, east and south of the roads went: the app city blocks stand there (city.ts)
  // north of the north road, between the sidewalk and the flyover
  [-44, -23.2], [-36, -23.2], [-30, -23.4], [-4, -23.4], [4, -23.4], [30, -23.4], [36, -23.2], [44, -23.2],
];

const ROADS = [-18.2, 18.2]; // two east-west and two north-south roads: four crossings
const ROAD_HALF = 2.7; // the roads are 5.4 m wide
const WALK = 1.2; // sidewalk width
const SIGNAL_CYCLE = 12; // seconds: green 5, amber 1, red 6 (the other road green, then amber)
const SIGNAL_ON = 1.6;
const SIGNAL_OFF = 0.06;

const CAR_COLORS = [0x6e76f0, 0x5cc98f, 0xe9b25c, 0xf4f1ea, 0xf07c7c, 0x9a6b12];

function box(w: number, h: number, d: number, mat: THREE.Material, x: number, y: number, z: number) {
  const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mat);
  m.position.set(x, y, z);
  m.receiveShadow = true;
  return m;
}

type Place = { x: number; y: number; z: number; ry?: number; s?: [number, number, number] };

/** Many copies of one shape in one draw call. */
function instanced(geometry: THREE.BufferGeometry, mat: THREE.Material, places: Place[]): THREE.InstancedMesh {
  const m = new THREE.InstancedMesh(geometry, mat, places.length);
  const o = new THREE.Object3D();
  places.forEach((p, i) => {
    o.position.set(p.x, p.y, p.z);
    o.rotation.set(0, p.ry ?? 0, 0);
    o.scale.set(...(p.s ?? [1, 1, 1]));
    o.updateMatrix();
    m.setMatrixAt(i, o.matrix);
  });
  m.receiveShadow = true;
  return m;
}

/** Spots on both sidewalks of every road, every 8 m out to ±44 m and clear of the crossings. ry turns a street light's
 *  arm (+x) toward the road. The north-south roads get no HQ-side spots past the crossings: the south block is there. */
function alongRoads(start: number, offset: number): Place[] {
  const spots: Place[] = [];
  for (const at of ROADS) {
    for (let p = start; p <= 44; p += 8) {
      if (ROADS.some((c) => Math.abs(p - c) < 4.5)) continue;
      for (const side of [1, -1]) {
        const c = at + side * offset;
        spots.push({ x: p, y: 0, z: c, ry: side > 0 ? Math.PI / 2 : -Math.PI / 2 }); // east-west road
        const hqSide = side === -Math.sign(at);
        if (!(hqSide && Math.abs(p) > 22)) spots.push({ x: c, y: 0, z: p, ry: side > 0 ? Math.PI : 0 }); // north-south road
      }
    }
  }
  return spots;
}

export function buildEnvironment(scene: THREE.Scene): Environment {
  const env = new THREE.Group();
  const std = (color: number, roughness: number) => new THREE.MeshStandardMaterial({ color, roughness });
  const grass = std(0x0f261e, 0.92);
  const lawn = std(0x16382c, 0.85);
  const sidewalk = std(0x1d2842, 0.8);
  const road = std(0x141b2d, 0.88);
  const divider = std(0x26324d, 0.65);
  const zebra = std(0xf4f1ea, 0.6); // white in both themes
  const metal = std(0x2a3557, 0.5); // street light and traffic light poles
  metal.userData.light = 0x5f6878;

  env.add(box(150, 0.4, 150, grass, 0, -0.75, 0));
  for (const [x, z, w, d] of [
    [0, -13.4, 28, 3.2],
    [0, 13.4, 28, 3.2],
    [-13.4, 0, 3.2, 23.6],
    [13.4, 0, 3.2, 23.6],
  ]) {
    env.add(box(w, 0.22, d, lawn, x, -0.44, z));
  }
  env.add(box(25.2, 0.3, 25.2, sidewalk, 0, -0.43, 0));

  // Roads: north and south along x, west and east along z; plain asphalt, no center lines
  for (const at of ROADS) {
    env.add(box(140, 0.18, ROAD_HALF * 2, road, 0, -0.46, at));
    env.add(box(ROAD_HALF * 2, 0.18, 140, road, at, -0.45, 0));
  }

  // Raised sidewalks on both sides of every road: the east-west ones run through the corners, the north-south ones
  // stop at them, so nothing overlaps
  const walkOffset = ROAD_HALF + WALK / 2;
  const ewSpans: [number, number][] = [[-70, -20.9], [-15.5, 15.5], [20.9, 70]];
  const nsSpans: [number, number][] = [[-70, -22.1], [-14.3, 14.3], [22.1, 70]];
  for (const at of ROADS) {
    for (const side of [1, -1]) {
      for (const [a, b] of ewSpans) env.add(box(b - a, 0.24, WALK, sidewalk, (a + b) / 2, -0.42, at + side * walkOffset));
      for (const [a, b] of nsSpans) env.add(box(WALK, 0.24, b - a, sidewalk, at + side * walkOffset, -0.42, (a + b) / 2));
    }
  }

  // Zebra crossings on all four sides of each crossing
  const stripes: Place[] = [];
  for (const cx of ROADS) {
    for (const cz of ROADS) {
      for (const side of [1, -1]) {
        for (let k = -4; k <= 4; k++) {
          stripes.push({ x: cx + side * (ROAD_HALF + 0.75), y: -0.355, z: cz + k * 0.6 }); // across the east-west road
          stripes.push({ x: cx + k * 0.6, y: -0.355, z: cz + side * (ROAD_HALF + 0.75), ry: Math.PI / 2 }); // and the other
        }
      }
    }
  }
  env.add(instanced(new THREE.BoxGeometry(1.1, 0.02, 0.32), zebra, stripes));

  // Traffic lights on the four corners of each crossing: two face the east-west road, two the north-south one. Their
  // lamps (red, amber, green from the top) share one material per road and color, which updateTraffic switches.
  const signal = (color: number) =>
    new THREE.MeshStandardMaterial({ color: 0x2a2f3a, emissive: color, emissiveIntensity: SIGNAL_OFF, roughness: 0.3 });
  const signals = [0, 1].map(() => ({
    red: signal(0xf07c7c),
    amber: signal(0xe9b25c),
    green: signal(0x5cc98f),
  })) as Environment["signals"];
  const corners: [Place[], Place[]] = [[], []];
  for (const cx of ROADS) {
    for (const cz of ROADS) {
      for (const [sx, sz] of [[1, 1], [-1, -1], [1, -1], [-1, 1]]) {
        corners[sx === sz ? 0 : 1].push({ x: cx + sx * 3.6, y: 0, z: cz + sz * 3.6 });
      }
    }
  }
  const poles = [...corners[0], ...corners[1]];
  env.add(instanced(new THREE.CylinderGeometry(0.06, 0.07, 2.4, 8), metal, poles.map((c) => ({ ...c, y: 0.9 }))));
  env.add(instanced(new THREE.BoxGeometry(0.14, 0.62, 0.14), metal, poles.map((c) => ({ ...c, y: 2.4 }))));
  const lampShape = new THREE.SphereGeometry(0.085, 10, 8);
  corners.forEach((list, g) => {
    (["red", "amber", "green"] as const).forEach((color, k) => {
      env.add(instanced(lampShape, signals[g][color], list.map((c) => ({ ...c, y: 2.6 - k * 0.2 }))));
    });
  });

  // Street lights: a pole, an arm reaching over the road and a head that glows at night (setStreetLights)
  const lamp = new THREE.MeshStandardMaterial({ color: 0xfff3d6, emissive: 0xffd98a, emissiveIntensity: 0, roughness: 0.3 });
  const lights = alongRoads(-44, walkOffset);
  const arm = new THREE.BoxGeometry(0.75, 0.06, 0.06).translate(0.375, 0, 0);
  const head = new THREE.BoxGeometry(0.34, 0.08, 0.18).translate(0.72, -0.04, 0);
  env.add(instanced(new THREE.CylinderGeometry(0.05, 0.07, 2.9, 8), metal, lights.map((l) => ({ ...l, y: 1.1 }))));
  env.add(instanced(arm, metal, lights.map((l) => ({ ...l, y: 2.52 }))));
  env.add(instanced(head, lamp, lights.map((l) => ({ ...l, y: 2.5 }))));

  // Low-poly trees
  const trunk = std(0x5c4028, 0.85);
  const leavesDark = std(0x28664b, 0.75);
  const leavesLight = std(0x3b855f, 0.75);
  TREES.forEach(([x, z], i) => {
    const tree = new THREE.Group();
    const s = 0.85 + (i % 3) * 0.2;
    const parts: [THREE.BufferGeometry, THREE.Material, number][] = [
      [new THREE.CylinderGeometry(0.14 * s, 0.22 * s, 0.9 * s, 8), trunk, 0.45 * s],
      [new THREE.ConeGeometry(0.85 * s, 1.5 * s, 7), i % 2 ? leavesLight : leavesDark, 1.35 * s],
      [new THREE.ConeGeometry(0.62 * s, 1.2 * s, 7), i % 2 ? leavesDark : leavesLight, 2.05 * s],
    ];
    for (const [geometry, mat, y] of parts) {
      const part = new THREE.Mesh(geometry, mat);
      part.position.y = y;
      part.castShadow = true;
      tree.add(part);
    }
    tree.position.set(x, -0.35, z);
    env.add(tree);
  });

  // Bushes: on the sidewalks halfway between the street lights, and in a row along the HQ's lawns
  const bushes: Place[] = alongRoads(-40, walkOffset).map((b, i) => ({ ...b, y: -0.12, ry: i, s: [1, 0.72, 1] }));
  for (let p = -11; p <= 11; p += 2.2) {
    if ([-8.5, 8.5].some((t) => Math.abs(p - t) < 1)) continue; // the lawn trees stand there
    for (const side of [1, -1]) {
      const small: [number, number, number] = [0.85, 0.62, 0.85];
      bushes.push({ x: p, y: -0.2, z: side * 12.95, ry: p, s: small }, { x: side * 12.95, y: -0.2, z: p, ry: p, s: small });
    }
  }
  const bushShape = new THREE.DodecahedronGeometry(0.42, 0);
  env.add(instanced(bushShape, leavesDark, bushes.filter((_, i) => i % 2 === 0)));
  env.add(instanced(bushShape, leavesLight, bushes.filter((_, i) => i % 2 === 1)));

  // Flyover in the north background
  env.add(box(140, 0.45, 4.2, divider, 0, 3.4, -27.5), box(140, 0.12, 3.6, road, 0, 3.65, -27.5));
  for (let x = -48; x <= 48; x += 16) {
    const pier = new THREE.Mesh(new THREE.CylinderGeometry(0.45, 0.55, 4.0, 12), divider);
    pier.position.set(x, 1.4, -27.5);
    pier.castShadow = true;
    env.add(pier);
  }

  // Cars
  const cabin = new THREE.MeshStandardMaterial({ color: 0xfffdf8, roughness: 0.2 });
  const cars = LANES.map((lane, i) => {
    const car = new THREE.Group();
    const body = new THREE.Mesh(
      new THREE.BoxGeometry(1.35, 0.32, 0.72),
      new THREE.MeshStandardMaterial({ color: CAR_COLORS[i % CAR_COLORS.length], roughness: 0.35, metalness: 0.2 }),
    );
    body.position.y = 0.18;
    body.castShadow = true;
    const top = new THREE.Mesh(new THREE.BoxGeometry(0.72, 0.26, 0.62), cabin);
    top.position.set(-0.05, 0.44, 0);
    car.add(body, top);
    if (lane.axis === "x") {
      car.position.set(lane.start, lane.y, lane.fixed);
      if (lane.dir < 0) car.rotation.y = Math.PI;
    } else {
      car.position.set(lane.fixed, lane.y, lane.start);
      car.rotation.y = lane.dir > 0 ? -Math.PI / 2 : Math.PI / 2;
    }
    env.add(car);
    return { mesh: car, axis: lane.axis, dir: lane.dir, speed: lane.speed };
  });

  scene.add(env);
  const environment = { cars, signals, signalTime: 0, lamp };
  updateTraffic(environment, 0); // light the first signal state (with reduced motion the lights then stay as they are)
  return environment;
}

/** Street lights on at night (the PHT clock decides, like the sun). */
export function setStreetLights(environment: Environment, night: boolean): void {
  environment.lamp.emissiveIntensity = night ? 1.4 : 0;
}

/** Drive the cars (each wraps around at ±48 m) and step the traffic lights. The cars are decoration: they don't stop. */
export function updateTraffic(environment: Environment, dt: number): void {
  environment.signalTime = (environment.signalTime + dt) % SIGNAL_CYCLE;
  const half = SIGNAL_CYCLE / 2;
  environment.signals.forEach((lamps, g) => {
    const t = (environment.signalTime + g * half) % SIGNAL_CYCLE; // the other road runs half a cycle behind
    const lit = t < half - 1 ? "green" : t < half ? "amber" : "red";
    for (const color of ["red", "amber", "green"] as const) {
      lamps[color].emissiveIntensity = color === lit ? SIGNAL_ON : SIGNAL_OFF;
    }
  });
  for (const car of environment.cars) {
    const position = car.mesh.position;
    position[car.axis] += car.dir * car.speed * dt;
    if (car.dir > 0 && position[car.axis] > 48) position[car.axis] = -48;
    if (car.dir < 0 && position[car.axis] < -48) position[car.axis] = 48;
  }
}

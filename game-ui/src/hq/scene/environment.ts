import * as THREE from "three";

// What surrounds the HQ: a park with lawns and trees, four roads with lane dashes, a flyover in the north and a few
// cars driving around. Decoration only: nothing here is clickable.

type Car = { mesh: THREE.Group; axis: "x" | "z"; dir: 1 | -1; speed: number };

export type Environment = { cars: Car[] };

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
  [-23.5, -23.5], [-28.0, -12.0], [-24.0, 6.0], [-26.0, 23.5],
  [23.5, -23.5], [27.0, -10.0], [24.5, 8.0], [25.5, 24.0],
  [-11.0, -23.0], [11.0, -23.0], [-12.0, 24.0], [12.0, 24.0],
];

const CAR_COLORS = [0x6e76f0, 0x5cc98f, 0xe9b25c, 0xf4f1ea, 0xf07c7c, 0x9a6b12];

function box(w: number, h: number, d: number, mat: THREE.Material, x: number, y: number, z: number) {
  const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mat);
  m.position.set(x, y, z);
  m.receiveShadow = true;
  return m;
}

export function buildEnvironment(scene: THREE.Scene): Environment {
  const env = new THREE.Group();
  const std = (color: number, roughness: number) => new THREE.MeshStandardMaterial({ color, roughness });
  const grass = std(0x0f261e, 0.92);
  const lawn = std(0x16382c, 0.85);
  const sidewalk = std(0x1d2842, 0.8);
  const road = std(0x141b2d, 0.88);
  const divider = std(0x26324d, 0.65);
  const dash = new THREE.MeshBasicMaterial({ color: 0xe9b25c });
  dash.userData.light = 0xfffdf8; // white lane dashes on a grey road (the amber stays amber elsewhere)

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

  // Roads: north and south along x, west and east along z, each with a median and dashed lanes
  for (const at of [-18.2, 18.2]) {
    env.add(box(140, 0.18, 5.4, road, 0, -0.46, at));
    env.add(box(140, 0.34, 0.24, divider, 0, -0.28, at));
    env.add(box(5.4, 0.18, 140, road, at, -0.45, 0));
    env.add(box(0.24, 0.34, 140, divider, at, -0.27, 0));
    for (let p = -60; p <= 60; p += 4.5) {
      if (Math.abs(p) > 15 && Math.abs(p) < 21) continue; // keep the crossings clear
      env.add(box(1.8, 0.04, 0.12, dash, p, -0.36, at - 1.35), box(1.8, 0.04, 0.12, dash, p, -0.36, at + 1.35));
      env.add(box(0.12, 0.04, 1.8, dash, at - 1.35, -0.35, p), box(0.12, 0.04, 1.8, dash, at + 1.35, -0.35, p));
    }
  }

  // Flyover in the north background
  env.add(box(140, 0.45, 4.2, divider, 0, 3.4, -27.5), box(140, 0.12, 3.6, road, 0, 3.65, -27.5));
  for (let x = -48; x <= 48; x += 16) {
    const pier = new THREE.Mesh(new THREE.CylinderGeometry(0.45, 0.55, 4.0, 12), divider);
    pier.position.set(x, 1.4, -27.5);
    pier.castShadow = true;
    env.add(pier);
  }

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
  return { cars };
}

/** Drive the cars; each wraps around at ±48 m. */
export function updateTraffic(environment: Environment, dt: number): void {
  for (const car of environment.cars) {
    const position = car.mesh.position;
    position[car.axis] += car.dir * car.speed * dt;
    if (car.dir > 0 && position[car.axis] > 48) position[car.axis] = -48;
    if (car.dir < 0 && position[car.axis] < -48) position[car.axis] = 48;
  }
}

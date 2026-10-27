import * as THREE from "three";

// The HQ's staff (V3, from the design mock): seven people, each walking back and forth between two points in a wing,
// slowing at the ends, facing the way they walk, legs and arms swinging. Decoration only: not clickable, the same
// colors in both themes (keepColors, like Xia). The mock's paths crossed or grazed some of our props, so six were moved
// (every path now keeps ≥ 0.45 m from props and walls).

// a, b: the two ends of the walk in the parent's coordinates; y: the floor height (default 0.14 = the HQ floor)
export type WalkerSpec = {
  name: string;
  a: [number, number];
  b: [number, number];
  speed: number;
  jacket: number;
  hair: number;
  phase: number;
  y?: number;
};

const STAFF: WalkerSpec[] = [
  // Monitor · Control Room
  { name: "Elena · NOC", a: [-5.3, -8.8], b: [-5.0, -5.4], speed: 1.35, jacket: 0x5cc98f, hair: 0x1a202c, phase: 0 },
  { name: "Dante · Audit", a: [-8.6, -5.0], b: [-4.8, -4.8], speed: 1.15, jacket: 0xe9b25c, hair: 0x2d3748, phase: 1.4 },
  // Knowledge · Library
  { name: "Sofia · Docs", a: [5.0, -5.6], b: [8.6, -5.6], speed: 1.25, jacket: 0x6e76f0, hair: 0x0a1128, phase: 2.1 },
  { name: "Liam · RAG", a: [6.0, -4.4], b: [8.6, -2.0], speed: 1.4, jacket: 0x5cc98f, hair: 0x4a3525, phase: 0.8 },
  // Clients · Embassy
  { name: "Hannah · Embassy", a: [-5.0, 2.3], b: [-2.8, 5.8], speed: 1.3, jacket: 0x6e76f0, hair: 0x1a202c, phase: 3 },
  { name: "Miguel · Vault", a: [-9.2, 6.1], b: [-4.8, 6.3], speed: 1.1, jacket: 0xe9b25c, hair: 0x0a1128, phase: 4.2 },
  // Admin · Engine Room
  { name: "Rico · SecOps", a: [3.2, 4.4], b: [6.6, 7.8], speed: 1.35, jacket: 0xf07c7c, hair: 0x1a202c, phase: 1.9 },
];

export type Walker = {
  group: THREE.Group;
  spec: WalkerSpec;
  t: number;
  legs: [THREE.Mesh, THREE.Mesh];
  arms: [THREE.Mesh, THREE.Mesh];
};

function part(geometry: THREE.BufferGeometry, mat: THREE.Material, x: number, y: number, z: number) {
  const m = new THREE.Mesh(geometry, mat);
  m.position.set(x, y, z);
  m.castShadow = true;
  return m;
}

function place(walker: Walker): void {
  const { a, b } = walker.spec;
  const along = (Math.sin(walker.t) + 1) / 2; // 0 → 1 → 0, slow at both ends
  const x = THREE.MathUtils.lerp(a[0], b[0], along);
  const z = THREE.MathUtils.lerp(a[1], b[1], along);
  const { position } = walker.group;
  const dx = x - position.x;
  const dz = z - position.z;
  if (Math.hypot(dx, dz) > 0.001) walker.group.rotation.y = Math.atan2(dx, dz);
  position.set(x, walker.spec.y ?? 0.14, z);
}

export function buildStaff(scene: THREE.Scene): Walker[] {
  return buildWalkers(scene, STAFF);
}

/** People walking back and forth under parent (the scene, or a city block for its app engineer). */
export function buildWalkers(parent: THREE.Object3D, specs: WalkerSpec[]): Walker[] {
  // Shared by everyone: one set of shapes, the trousers, the sleeves and the skin (built per scene: the scene's
  // teardown disposes them)
  const LEG = new THREE.CylinderGeometry(0.065, 0.055, 0.36, 8);
  const ARM = new THREE.CylinderGeometry(0.05, 0.045, 0.34, 8);
  const TORSO = new THREE.CylinderGeometry(0.15, 0.2, 0.46, 12);
  const HEAD = new THREE.SphereGeometry(0.18, 14, 14);
  const HAIR = new THREE.SphereGeometry(0.19, 12, 12, 0, Math.PI * 2, 0, Math.PI * 0.58);
  const FLOOR_RING = new THREE.RingGeometry(0.24, 0.31, 20);
  const trousers = new THREE.MeshStandardMaterial({ color: 0x1e293b, roughness: 0.6 });
  const sleeves = new THREE.MeshStandardMaterial({ color: 0xf4f1ea, roughness: 0.45 });
  const skin = new THREE.MeshStandardMaterial({ color: 0xfffdf8, roughness: 0.4 });

  return specs.map((spec) => {
    const group = new THREE.Group();
    const jacket = new THREE.MeshStandardMaterial({ color: spec.jacket, roughness: 0.4 });
    const legs: Walker["legs"] = [part(LEG, trousers, -0.09, 0.18, 0), part(LEG, trousers, 0.09, 0.18, 0)];
    const arms: Walker["arms"] = [part(ARM, sleeves, -0.22, 0.55, 0), part(ARM, sleeves, 0.22, 0.55, 0)];
    const hair = part(HAIR, new THREE.MeshStandardMaterial({ color: spec.hair, roughness: 0.5 }), 0, 0.98, -0.02);
    hair.rotation.x = -0.2;
    const ring = new THREE.Mesh(
      FLOOR_RING,
      new THREE.MeshBasicMaterial({ color: spec.jacket, side: THREE.DoubleSide, transparent: true, opacity: 0.55 }),
    );
    ring.rotation.x = -Math.PI / 2;
    ring.position.y = 0.02;
    group.add(...legs, ...arms, part(TORSO, jacket, 0, 0.56, 0), part(HEAD, skin, 0, 0.96, 0), hair, ring);
    group.name = spec.name;
    group.userData.keepColors = true; // the same people in both themes (palette.ts skips them)
    parent.add(group);

    const walker: Walker = { group, spec, t: spec.phase, legs, arms };
    place(walker);
    return walker;
  });
}

/** Walk everyone on; skipped when motion is reduced (they stand still where they are). */
export function updateStaff(staff: Walker[], dt: number): void {
  for (const walker of staff) {
    walker.t += dt * walker.spec.speed * 0.45;
    place(walker);
    const swing = Math.sin(walker.t * 6.5) * 0.45;
    walker.legs[0].rotation.x = swing;
    walker.legs[1].rotation.x = -swing;
    walker.arms[0].rotation.x = -swing * 0.7;
    walker.arms[1].rotation.x = swing * 0.7;
  }
}

import * as THREE from "three";

import type { Pht } from "@/hq/pht";

// The PHT clock tower north of the HQ, between the north road and the flyover (V2, from the design mock): a stepped
// pedestal, a shaft with gold pilasters, a belfry with a dial facing the plaza, a spire and a green finial. Its hands
// show Manila time (or the simulated time). Clicking it opens /clock-tower (userData.stationId), super admins only.

export type ClockTower = {
  group: THREE.Group;
  hour: THREE.Group;
  minute: THREE.Group;
  second: THREE.Group;
};

export const CLOCK_POSITION = { x: 0, z: -23.3 }; // clear of the road (z −20.9) and the flyover (z −25.4)
const DIAL_Y = 8.05;

function box(w: number, h: number, d: number, mat: THREE.Material, x: number, y: number, z: number) {
  const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mat);
  m.position.set(x, y, z);
  return m;
}

function hand(width: number, length: number, color: number): THREE.Group {
  const pivot = new THREE.Group();
  const m = box(width, length, 0.04, new THREE.MeshBasicMaterial({ color }), 0, length * 0.42, 0);
  pivot.add(m);
  return pivot;
}

export function buildClockTower(scene: THREE.Scene): ClockTower {
  const group = new THREE.Group();
  group.position.set(CLOCK_POSITION.x, -0.55, CLOCK_POSITION.z); // on the grass

  const base = new THREE.MeshStandardMaterial({ color: 0x223059, roughness: 0.7 });
  const shaft = new THREE.MeshStandardMaterial({ color: 0x1b274a, roughness: 0.65 });
  const trim = new THREE.MeshStandardMaterial({ color: 0x9a6b12, roughness: 0.35, metalness: 0.3 });

  group.add(box(4.6, 0.45, 4.6, base, 0, 0.05, 0), box(3.2, 1.8, 3.2, base, 0, 1.1, 0), box(2.3, 4.8, 2.3, shaft, 0, 4.4, 0));
  for (const [x, z] of [[-1.12, -1.12], [1.12, -1.12], [-1.12, 1.12], [1.12, 1.12]]) {
    group.add(box(0.18, 4.8, 0.18, trim, x, 4.4, z));
  }
  group.add(box(2.65, 2.5, 2.65, base, 0, DIAL_Y, 0));
  const roof = new THREE.Mesh(new THREE.ConeGeometry(2.05, 2.2, 4), trim);
  roof.position.y = 10.4;
  roof.rotation.y = Math.PI / 4;
  group.add(roof);
  const finial = new THREE.Mesh(
    new THREE.OctahedronGeometry(0.32, 0),
    new THREE.MeshStandardMaterial({ color: 0x5cc98f, emissive: 0x5cc98f, emissiveIntensity: 0.75 }),
  );
  finial.position.y = 11.75;
  group.add(finial);

  // The dial faces the plaza (+z): gold bezel, paper face, 12 markers
  const bezel = new THREE.Mesh(new THREE.CylinderGeometry(1.12, 1.12, 0.16, 32), trim);
  bezel.rotation.x = Math.PI / 2;
  bezel.position.set(0, DIAL_Y, 1.32);
  const dial = new THREE.Mesh(
    new THREE.CylinderGeometry(0.98, 0.98, 0.18, 32),
    new THREE.MeshStandardMaterial({ color: 0xfffdf8, emissive: 0xfffdf8, emissiveIntensity: 0.28, roughness: 0.3 }),
  );
  dial.rotation.x = Math.PI / 2;
  dial.position.set(0, DIAL_Y, 1.34);
  group.add(bezel, dial);
  const marker = new THREE.MeshBasicMaterial({ color: 0x0a1128 });
  for (let h = 0; h < 12; h++) {
    const angle = (h / 12) * Math.PI * 2;
    const quarter = h % 3 === 0;
    const tick = box(quarter ? 0.09 : 0.05, quarter ? 0.2 : 0.12, 0.04, marker, Math.sin(angle) * 0.78, DIAL_Y + Math.cos(angle) * 0.78, 1.44);
    tick.rotation.z = -angle;
    group.add(tick);
  }

  // Hands turn around the dial's center; rotation.z < 0 = clockwise seen from the plaza
  const center = new THREE.Group();
  center.position.set(0, DIAL_Y, 1.46);
  const hour = hand(0.085, 0.5, 0x0a1128);
  const minute = hand(0.06, 0.72, 0x0a1128);
  const second = hand(0.03, 0.8, 0xb3261e);
  const pin = new THREE.Mesh(new THREE.SphereGeometry(0.08, 12, 12), trim);
  center.add(hour, minute, second, pin);
  group.add(center);

  group.traverse((child) => {
    child.userData.stationId = "clock";
    if (child instanceof THREE.Mesh) {
      child.castShadow = true;
      child.receiveShadow = true;
    }
  });
  scene.add(group);
  return { group, hour, minute, second };
}

/** Point the hands at the time. */
export function updateClock(tower: ClockTower, pht: Pht): void {
  const turn = Math.PI * 2;
  tower.second.rotation.z = -(pht.seconds / 60) * turn;
  tower.minute.rotation.z = -((pht.minutes + pht.seconds / 60) / 60) * turn;
  tower.hour.rotation.z = -(((pht.hours % 12) + pht.minutes / 60) / 12) * turn;
}

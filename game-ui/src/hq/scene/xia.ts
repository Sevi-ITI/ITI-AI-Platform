import * as THREE from "three";

// Xia, the HQ's guide: a small figure who walks to wherever the person taps, or to the room they open. A green
// plumbob floats over her head; a marker shows where she is heading.

const SPEED = 6.2; // m/s
const LIMIT = 9.4; // she stays inside the building, except on a trip to a city block (V4)
const CITY_LIMIT = 58;
const INSIDE = 12.6; // the HQ's plinth: inside it she stands on its floor, outside on the city's sidewalks

function floorY(x: number, z: number): number {
  return Math.abs(x) < INSIDE && Math.abs(z) < INSIDE ? 0.14 : -0.22;
}

export class Xia {
  readonly group = new THREE.Group();
  readonly position = new THREE.Vector2(0, 2.2); // x, z
  isMoving = false;

  private readonly target = new THREE.Vector2(0, 2.2);
  private readonly marker = new THREE.Group();
  private readonly body = new THREE.Group();
  private readonly limbs: THREE.Mesh[] = []; // left leg, right leg, left arm, right arm
  private readonly plumbob: THREE.Mesh;
  private yaw = 0;
  private walkTime = 0;
  private onArrive: (() => void) | null = null;

  constructor(scene: THREE.Scene) {
    const std = (color: number, roughness = 0.4) => new THREE.MeshStandardMaterial({ color, roughness });
    const part = (geometry: THREE.BufferGeometry, mat: THREE.Material, x: number, y: number, z: number) => {
      const m = new THREE.Mesh(geometry, mat);
      m.position.set(x, y, z);
      m.castShadow = true;
      this.body.add(m);
      return m;
    };

    const leg = new THREE.CylinderGeometry(0.08, 0.07, 0.42, 12);
    const arm = new THREE.CylinderGeometry(0.06, 0.055, 0.4, 12);
    const trousers = std(0x17213f, 0.5);
    const sleeves = std(0xf4f1ea);
    this.limbs.push(part(leg, trousers, -0.11, 0.21, 0), part(leg, trousers, 0.11, 0.21, 0));
    part(new THREE.CylinderGeometry(0.18, 0.24, 0.54, 16), std(0x6e76f0, 0.35), 0, 0.64, 0); // jacket
    this.limbs.push(part(arm, sleeves, -0.26, 0.62, 0), part(arm, sleeves, 0.26, 0.62, 0));
    part(new THREE.SphereGeometry(0.22, 20, 20), std(0xfffdf8, 0.35), 0, 1.12, 0); // head
    const hairMat = std(0x0a1128, 0.45);
    const hair = part(new THREE.SphereGeometry(0.23, 18, 18, 0, Math.PI * 2, 0, Math.PI * 0.62), hairMat, 0, 1.14, -0.02);
    hair.rotation.x = -0.25;
    part(new THREE.SphereGeometry(0.1, 14, 14), hairMat, 0, 1.32, -0.16); // bun
    const eye = new THREE.SphereGeometry(0.032, 10, 10);
    const eyeMat = new THREE.MeshBasicMaterial({ color: 0x0a1128 });
    part(eye, eyeMat, -0.075, 1.12, 0.2);
    part(eye, eyeMat, 0.075, 1.12, 0.2);
    this.group.add(this.body);

    this.plumbob = new THREE.Mesh(
      new THREE.OctahedronGeometry(0.14, 0),
      new THREE.MeshStandardMaterial({ color: 0x5cc98f, emissive: 0x5cc98f, emissiveIntensity: 0.75, roughness: 0.15 }),
    );
    this.plumbob.scale.set(0.75, 1.35, 0.75);
    this.plumbob.position.y = 1.68;
    this.group.add(this.plumbob);

    const ring = (inner: number, outer: number, color: number) => {
      const m = new THREE.Mesh(
        new THREE.RingGeometry(inner, outer, 32),
        new THREE.MeshBasicMaterial({ color, side: THREE.DoubleSide, transparent: true, opacity: 0.85 }),
      );
      m.rotation.x = -Math.PI / 2;
      return m;
    };
    const base = ring(0.32, 0.44, 0x5cc98f);
    base.position.y = 0.02;
    this.group.add(base);
    this.group.position.set(this.position.x, 0.14, this.position.y);
    this.group.userData.keepColors = true; // the same Xia in both themes (palette.ts skips her)
    scene.add(this.group);

    const arrow = new THREE.Mesh(
      new THREE.ConeGeometry(0.14, 0.35, 16),
      new THREE.MeshBasicMaterial({ color: 0x5cc98f, transparent: true, opacity: 0.85 }),
    );
    arrow.rotation.x = Math.PI;
    arrow.position.y = 0.28;
    this.marker.add(ring(0.35, 0.52, 0x6e76f0), arrow);
    this.marker.visible = false;
    this.marker.userData.keepColors = true;
    scene.add(this.marker);
  }

  /** Walk to (x, z); onArrive runs once she gets there (not if another walk replaces this one). outside = a trip to
   *  a city block: she may leave the building. */
  walkTo(x: number, z: number, instant: boolean, onArrive: (() => void) | null = null, outside = false): void {
    const limit = outside ? CITY_LIMIT : LIMIT;
    this.target.set(THREE.MathUtils.clamp(x, -limit, limit), THREE.MathUtils.clamp(z, -limit, limit));
    this.onArrive = onArrive;
    if (instant) {
      this.position.copy(this.target);
      this.group.position.set(this.position.x, floorY(this.position.x, this.position.y), this.position.y);
      this.arrive();
      return;
    }
    this.isMoving = true;
    this.marker.position.set(this.target.x, floorY(this.target.x, this.target.y) + 0.02, this.target.y);
    this.marker.visible = true;
  }

  update(dt: number, seconds: number, reducedMotion: boolean): void {
    if (!reducedMotion) {
      this.plumbob.rotation.y = seconds * 2.2;
      this.plumbob.position.y = 1.68 + Math.sin(seconds * 3.5) * 0.05;
    }
    if (!this.isMoving) return;

    const dx = this.target.x - this.position.x;
    const dz = this.target.y - this.position.y;
    const distance = Math.hypot(dx, dz);
    if (distance < 0.12) {
      this.position.copy(this.target);
      this.arrive();
    } else {
      const step = Math.min(distance, SPEED * dt);
      this.position.x += (dx / distance) * step;
      this.position.y += (dz / distance) * step;

      // turn toward where she walks, the short way round
      let turn = Math.atan2(dx, dz) - this.yaw;
      while (turn > Math.PI) turn -= Math.PI * 2;
      while (turn < -Math.PI) turn += Math.PI * 2;
      this.yaw += turn * Math.min(1, dt * 14);
      this.group.rotation.y = this.yaw;

      this.walkTime += dt * 13;
      const swing = Math.sin(this.walkTime) * 0.65;
      const [leftLeg, rightLeg, leftArm, rightArm] = this.limbs;
      leftLeg.rotation.x = swing;
      rightLeg.rotation.x = -swing;
      leftArm.rotation.x = -swing * 0.8;
      rightArm.rotation.x = swing * 0.8;
      this.body.position.y = Math.abs(Math.sin(this.walkTime)) * 0.07;
      this.marker.rotation.y = seconds * 3;
    }
    this.group.position.set(this.position.x, floorY(this.position.x, this.position.y), this.position.y);
  }

  private arrive(): void {
    this.isMoving = false;
    this.marker.visible = false;
    for (const limb of this.limbs) limb.rotation.x = 0;
    this.body.position.y = 0;
    const done = this.onArrive;
    this.onArrive = null;
    done?.();
  }
}

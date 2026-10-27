import * as THREE from "three";

// The HQ camera, like the Sims build mode: it orbits a focus point on the floor. Q / E orbit 45°, R / F tilt,
// WASD or arrows pan, left-drag pans, right-drag (or Alt + drag) orbits, the wheel zooms toward the cursor, Home
// resets. Every move sets a target; update() eases toward it (or jumps there when motion is reduced).

const DEG = Math.PI / 180;

export const CAMERA = {
  fov: 32,
  pitch: 42, // degrees down from level
  minPitch: 30,
  maxPitch: 60,
  yaw: 45,
  yawStep: 45,
  distance: 28,
  minDistance: 12,
  maxDistance: 64,
  focusDistance: 14.2, // when a room is selected
  panLimit: 24, // the focus stays inside [-24, 24] on x and z
  panSpeed: 14, // m/s with the keyboard
  damping: 10,
  minCameraY: 2.5,
};

export class CameraController {
  readonly targetFocus = new THREE.Vector3();
  readonly currentFocus = new THREE.Vector3();
  targetYaw = CAMERA.yaw * DEG;
  currentYaw = this.targetYaw;
  targetPitch = CAMERA.pitch * DEG;
  currentPitch = this.targetPitch;
  targetDist = CAMERA.distance;
  currentDist = this.targetDist;
  isDragging = false;

  private readonly keys = new Set<string>();
  private dragMode: "none" | "pan" | "orbit" = "none";
  private lastPointer = { x: 0, y: 0 };
  private readonly raycaster = new THREE.Raycaster();
  private readonly floor = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0);
  private readonly removers: (() => void)[] = [];

  constructor(
    private readonly camera: THREE.PerspectiveCamera,
    private readonly canvas: HTMLCanvasElement,
    private readonly reducedMotion: () => boolean,
    private readonly onInteract: () => void, // e.g. close the dock and the camera bar
  ) {
    this.listen(window, "keydown", (e) => this.onKeyDown(e as KeyboardEvent));
    this.listen(window, "keyup", (e) => this.keys.delete((e as KeyboardEvent).code));
    this.listen(window, "blur", () => this.keys.clear());
    this.listen(canvas, "pointerdown", (e) => this.onPointerDown(e as PointerEvent));
    this.listen(window, "pointermove", (e) => this.onPointerMove(e as PointerEvent));
    this.listen(window, "pointerup", () => {
      this.dragMode = "none";
      this.isDragging = false;
    });
    this.listen(canvas, "wheel", (e) => this.onWheel(e as WheelEvent), { passive: false });
    this.listen(canvas, "contextmenu", (e) => e.preventDefault());
    this.apply();
  }

  dispose(): void {
    for (const remove of this.removers) remove();
  }

  /** Where a screen point hits the floor, or null. */
  floorPoint(clientX: number, clientY: number): THREE.Vector3 | null {
    const rect = this.canvas.getBoundingClientRect();
    const ndc = new THREE.Vector2(
      ((clientX - rect.left) / rect.width) * 2 - 1,
      -((clientY - rect.top) / rect.height) * 2 + 1,
    );
    this.raycaster.setFromCamera(ndc, this.camera);
    const hit = new THREE.Vector3();
    return this.raycaster.ray.intersectPlane(this.floor, hit);
  }

  orbitStep(direction: 1 | -1): void {
    this.targetYaw += direction * CAMERA.yawStep * DEG;
    this.snapIfReduced();
  }

  tiltStep(degrees: number): void {
    this.targetPitch += degrees * DEG;
    this.clamp();
    this.snapIfReduced();
  }

  zoomStep(factor: number): void {
    this.targetDist *= factor;
    this.clamp();
    this.snapIfReduced();
  }

  resetHome(): void {
    this.targetFocus.set(0, 0, 0);
    this.targetYaw = CAMERA.yaw * DEG;
    this.targetPitch = CAMERA.pitch * DEG;
    this.targetDist = CAMERA.distance;
    this.snapIfReduced();
  }

  /** Close up on a room. shiftRight moves the focus right so the room sits left of the HUD panel; a tall room (the
   *  clock tower) asks for a longer distance. */
  focusOn(x: number, z: number, shiftRight: number, distance: number = CAMERA.focusDistance): void {
    this.followTo(x, z, shiftRight);
    this.targetDist = distance;
    this.clamp();
    this.snapIfReduced();
  }

  /** Keep the focus on a point (Xia while she walks), same distance. */
  followTo(x: number, z: number, shiftRight: number): void {
    this.targetFocus.set(x + Math.cos(this.targetYaw) * shiftRight, 0, z - Math.sin(this.targetYaw) * shiftRight);
    this.clamp();
  }

  update(dt: number): void {
    const forward = new THREE.Vector3(-Math.sin(this.currentYaw), 0, -Math.cos(this.currentYaw));
    const right = new THREE.Vector3(Math.cos(this.currentYaw), 0, -Math.sin(this.currentYaw));
    const move = new THREE.Vector3();
    if (this.keys.has("KeyW") || this.keys.has("ArrowUp")) move.add(forward);
    if (this.keys.has("KeyS") || this.keys.has("ArrowDown")) move.sub(forward);
    if (this.keys.has("KeyD") || this.keys.has("ArrowRight")) move.add(right);
    if (this.keys.has("KeyA") || this.keys.has("ArrowLeft")) move.sub(right);
    if (move.lengthSq() > 0) {
      this.targetFocus.add(move.normalize().multiplyScalar(CAMERA.panSpeed * dt));
      this.clamp();
    }

    if (this.reducedMotion()) {
      this.snap();
    } else {
      const alpha = 1 - Math.exp(-CAMERA.damping * dt);
      this.currentFocus.lerp(this.targetFocus, alpha);
      this.currentYaw = THREE.MathUtils.lerp(this.currentYaw, this.targetYaw, alpha);
      this.currentPitch = THREE.MathUtils.lerp(this.currentPitch, this.targetPitch, alpha);
      this.currentDist = THREE.MathUtils.lerp(this.currentDist, this.targetDist, alpha);
    }
    this.apply();
  }

  private apply(): void {
    const level = this.currentDist * Math.cos(this.currentPitch);
    const height = Math.max(CAMERA.minCameraY, this.currentDist * Math.sin(this.currentPitch));
    this.camera.position.set(
      this.currentFocus.x + level * Math.sin(this.currentYaw),
      this.currentFocus.y + height,
      this.currentFocus.z + level * Math.cos(this.currentYaw),
    );
    this.camera.lookAt(this.currentFocus);
  }

  private clamp(): void {
    this.targetPitch = THREE.MathUtils.clamp(this.targetPitch, CAMERA.minPitch * DEG, CAMERA.maxPitch * DEG);
    this.targetDist = THREE.MathUtils.clamp(this.targetDist, CAMERA.minDistance, CAMERA.maxDistance);
    this.targetFocus.x = THREE.MathUtils.clamp(this.targetFocus.x, -CAMERA.panLimit, CAMERA.panLimit);
    this.targetFocus.z = THREE.MathUtils.clamp(this.targetFocus.z, -CAMERA.panLimit, CAMERA.panLimit);
    this.targetFocus.y = 0;
  }

  private snap(): void {
    this.currentFocus.copy(this.targetFocus);
    this.currentYaw = this.targetYaw;
    this.currentPitch = this.targetPitch;
    this.currentDist = this.targetDist;
  }

  private snapIfReduced(): void {
    if (this.reducedMotion()) this.snap();
  }

  private onKeyDown(e: KeyboardEvent): void {
    // Never steal keys from a form field, a button the person is on, or a key combination.
    const target = e.target instanceof Element ? e.target : null; // can be the window or the document
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    if (target?.closest("input, textarea, select, [contenteditable='true'], dialog")) return;
    this.keys.add(e.code);
    const steps: Record<string, () => void> = {
      KeyQ: () => this.orbitStep(-1),
      KeyE: () => this.orbitStep(1),
      KeyR: () => this.tiltStep(4),
      KeyF: () => this.tiltStep(-4),
      Home: () => this.resetHome(),
    };
    if (steps[e.code]) {
      e.preventDefault();
      steps[e.code]();
    }
  }

  private onPointerDown(e: PointerEvent): void {
    this.lastPointer = { x: e.clientX, y: e.clientY };
    this.onInteract();
    if (e.button === 2 || (e.button === 0 && e.altKey)) this.dragMode = "orbit";
    else if (e.button === 0 || e.button === 1) this.dragMode = "pan";
  }

  private onPointerMove(e: PointerEvent): void {
    if (this.dragMode === "none") return;
    const dx = e.clientX - this.lastPointer.x;
    const dy = e.clientY - this.lastPointer.y;
    this.lastPointer = { x: e.clientX, y: e.clientY };
    if (Math.abs(dx) + Math.abs(dy) > 0) this.isDragging = true;

    if (this.dragMode === "orbit") {
      this.targetYaw -= dx * 0.0065;
      this.targetPitch += dy * 0.0045;
    } else {
      const scale = this.currentDist * 0.0014;
      const right = new THREE.Vector3(Math.cos(this.currentYaw), 0, -Math.sin(this.currentYaw));
      const forward = new THREE.Vector3(-Math.sin(this.currentYaw), 0, -Math.cos(this.currentYaw));
      this.targetFocus.addScaledVector(right, -dx * scale).addScaledVector(forward, dy * scale);
    }
    this.clamp();
    this.snapIfReduced();
  }

  private onWheel(e: WheelEvent): void {
    e.preventDefault();
    this.onInteract();
    const before = this.targetDist;
    this.targetDist = THREE.MathUtils.clamp(
      before * (e.deltaY > 0 ? 1.11 : 0.9),
      CAMERA.minDistance,
      CAMERA.maxDistance,
    );
    const hit = e.deltaY < 0 ? this.floorPoint(e.clientX, e.clientY) : null;
    if (hit) this.targetFocus.lerp(new THREE.Vector3(hit.x, 0, hit.z), (1 - this.targetDist / before) * 0.42);
    this.clamp();
    this.snapIfReduced();
  }

  private listen(
    target: Window | HTMLElement,
    type: string,
    handler: (e: Event) => void,
    options?: AddEventListenerOptions,
  ): void {
    target.addEventListener(type, handler, options);
    this.removers.push(() => target.removeEventListener(type, handler, options));
  }
}

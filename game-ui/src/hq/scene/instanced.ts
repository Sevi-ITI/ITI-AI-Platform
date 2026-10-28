import * as THREE from "three";

// Many copies of one small shape (a stripe, a pole, a bush, a bench) in one draw call: the streets and parks around
// the HQ have hundreds of them (environment.ts, parks.ts).

/** Where one copy goes: its position, a turn around y and a scale. */
export type Place = { x: number; y: number; z: number; ry?: number; s?: [number, number, number] };

export function instanced(geometry: THREE.BufferGeometry, mat: THREE.Material, places: Place[]): THREE.InstancedMesh {
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

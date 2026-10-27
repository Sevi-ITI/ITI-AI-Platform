import * as THREE from "three";

import type { Theme } from "@/hq/theme";

// The scene is built in its dark colors. Light mode swaps each dark color for its light partner below, so nothing
// stays navy on cream paper. Light values from the design mockup (design/index.html, syncSceneThemeAndRoles).
// Status colors (ok, warn, error) and Xia are the same in both themes. A material can name its own light color
// in userData.light when its dark color is shared with something that must not change (the road dashes are the
// warn amber).

const FURNITURE_LIGHT = 0xd6cbb8; // every navy desk, shelf and cabinet becomes warm sand
const FURNITURE_DARK = [
  0x263563, 0x223059, 0x2e3f73, 0x2b3a6b, 0x283868, 0x2c3d70, 0x243461, 0x24325c, 0x263663, 0x293766, 0x23305a,
];

const LIGHT: Record<number, number> = {
  ...Object.fromEntries(FURNITURE_DARK.map((dark) => [dark, FURNITURE_LIGHT])),
  0x6e76f0: 0x9a6b12, // accent: indigo → gold
  0x4b56d2: 0x7a5410, // the screens' indigo glow → a deeper gold
  0x111a34: 0xe5dfd3, // plinth
  0x1e2b52: 0xe2dacb, // plaza
  0x1b274a: 0xe5dfd3, // clock tower shaft
  0x26335e: 0xcbbfa8, // pylon
  0x202d56: 0xded6c6, // walls
  0x070c1d: 0xd8d3c8, // a locked wing's floor
  0x162244: 0xefeae0, // Monitor wing floor
  0x182548: 0xf5f0e6, // Knowledge wing floor
  0x152040: 0xf2ede2, // Clients wing floor
  0x1b1f3c: 0xebe5d8, // Admin wing floor
  0x0f261e: 0x88b578, // grass
  0x16382c: 0x99c488, // lawns
  0x1d2842: 0xdfd7c6, // sidewalk
  0x141b2d: 0x727882, // roads
  0x26324d: 0xc8bfae, // road dividers, flyover
  0x28664b: 0x468956, // leaves
  0x3b855f: 0x5ca16b, // leaves
};

/** The background and the light bounced off the ground. The sun and sky light follow the time of day (sun.ts). */
export const SKY: Record<Theme, { background: number; ground: number }> = {
  dark: { background: 0x0a1128, ground: 0x111a34 },
  light: { background: 0xe8e2d5, ground: 0xd5cbb8 },
};

type Tinted = THREE.Material & { color?: THREE.Color; emissive?: THREE.Color };

function forTheme(dark: number, theme: Theme, own?: number): number {
  return theme === "light" ? (own ?? LIGHT[dark] ?? dark) : dark;
}

/**
 * Give one material its colors for the theme. Its dark colors are remembered in userData the first time; code that
 * changes a color later (the beacon, a locked floor) sets userData.dark / darkEmissive first, then calls this.
 */
export function recolor(material: THREE.Material, theme: Theme): void {
  const m = material as Tinted;
  if (m.color) {
    m.userData.dark ??= m.color.getHex();
    m.color.setHex(forTheme(m.userData.dark, theme, m.userData.light));
  }
  if (m.emissive) {
    m.userData.darkEmissive ??= m.emissive.getHex();
    m.emissive.setHex(forTheme(m.userData.darkEmissive, theme));
  }
}

/** Recolor every mesh under root, except groups marked userData.keepColors (Xia). */
export function recolorTree(root: THREE.Object3D, theme: Theme): void {
  if (root.userData.keepColors) return;
  if (root instanceof THREE.Mesh) {
    const materials: THREE.Material[] = Array.isArray(root.material) ? root.material : [root.material];
    for (const m of materials) recolor(m, theme);
  }
  for (const child of root.children) recolorTree(child, theme);
}

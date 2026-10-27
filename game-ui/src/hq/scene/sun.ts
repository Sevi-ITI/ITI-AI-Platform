import * as THREE from "three";

import type { Pht } from "@/hq/pht";
import { SKY } from "@/hq/scene/palette";
import type { World } from "@/hq/scene/world";
import type { Theme } from "@/hq/theme";

// The light follows Manila's time of day (V2, from the design mock): by day the sun rises in the east (+x), stands
// high at noon and sets in the west, warmer near sunrise and sunset; by night a cool, dim moonlight from the
// north-west. The theme sets only the ground's bounce color and how the night sky tints the scene (indigo on navy,
// a pale blue on cream). Intensities are the mock's (r128) × π (physical lights since r155).

export function applySun(world: World, pht: Pht, theme: Theme): void {
  const { sun, hemi } = world;
  hemi.groundColor.setHex(SKY[theme].ground);
  if (pht.isDaylight) {
    const progress = THREE.MathUtils.clamp((pht.fractionalHour - 5.8) / 12.2, 0.02, 0.98);
    const angle = progress * Math.PI; // 0 = east horizon, π/2 = overhead, π = west horizon
    const height = Math.sin(angle);
    const warmth = 1 - height; // 1 near sunrise and sunset, 0 at noon
    sun.position.set(Math.cos(angle) * 34, Math.max(8, height * 36), 14 - height * 6);
    sun.color.setRGB(1, 0.99 - warmth * 0.11, 0.96 - warmth * 0.24, THREE.SRGBColorSpace);
    const paper = theme === "light" ? 0.7 : 1; // cream surfaces under full sun wash out to white: dim the day a little
    sun.intensity = (0.82 + height * 0.35) * Math.PI * paper;
    hemi.color.setRGB(0.96, 0.95 - warmth * 0.06, 0.92 - warmth * 0.1, THREE.SRGBColorSpace);
    hemi.intensity = (0.78 + height * 0.22) * Math.PI * paper;
  } else {
    sun.position.set(-18, 24, -14);
    sun.color.setHex(0xa8b8f8);
    sun.intensity = 0.55 * Math.PI;
    hemi.color.setHex(theme === "dark" ? 0x6e76f0 : 0xd8dcef);
    hemi.intensity = (theme === "dark" ? 0.62 : 0.7) * Math.PI;
  }
}

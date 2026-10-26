// Has game-ui caught up with admin-ui? Lists every FastAPI call admin-ui makes (method + path) and the ones
// game-ui does not make yet. Fails while anything is missing. Run from game-ui\: npm run check:parity.
// Half of the proof only: the same endpoint is not always the same feature, so the per-page feature checklist
// must also be ticked off before admin-ui can be retired.

import { readdirSync, readFileSync, statSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const gameUi = join(dirname(fileURLToPath(import.meta.url)), "..");
const adminUi = join(gameUi, "..", "admin-ui");

// api.GET("/v1/...") through the typed client, and fetch(`${apiUrl()}/v1/...`) in route handlers (streams, uploads)
const TYPED_CALL = /\bapi\.(GET|POST|PUT|PATCH|DELETE)\(\s*"(\/v1\/[^"]+)"/g;
const RAW_FETCH = /fetch\(\s*`\$\{apiUrl\(\)\}(\/v1\/[^`?]+)/g;

/** Source files under dir (.ts / .tsx; not the generated .d.ts types). */
function sourceFiles(dir) {
  const found = [];
  for (const name of readdirSync(dir)) {
    const full = join(dir, name);
    if (statSync(full).isDirectory()) found.push(...sourceFiles(full));
    else if (/\.tsx?$/.test(name) && !name.endsWith(".d.ts")) found.push(full);
  }
  return found;
}

function callsIn(app) {
  const calls = new Set();
  for (const file of sourceFiles(join(app, "src"))) {
    const text = readFileSync(file, "utf8");
    for (const m of text.matchAll(TYPED_CALL)) calls.add(`${m[1]} ${m[2]}`);
    for (const m of text.matchAll(RAW_FETCH)) calls.add(`fetch ${m[1]}`);
  }
  return calls;
}

const admin = callsIn(adminUi);
const game = callsIn(gameUi);
const missing = [...admin].filter((c) => !game.has(c)).sort();

console.log(`admin-ui makes ${admin.size} FastAPI calls; game-ui makes ${admin.size - missing.length} of them.`);
if (missing.length > 0) {
  console.log(`Missing in game-ui (${missing.length}):`);
  for (const c of missing) console.log(`  ${c}`);
  process.exit(1);
}
console.log("OK: game-ui makes every FastAPI call admin-ui makes.");

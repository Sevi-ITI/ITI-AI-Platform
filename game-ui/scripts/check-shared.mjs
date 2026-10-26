// The two consoles share how they talk to FastAPI and hold the session: game-ui keeps exact copies of
// admin-ui's src/lib/api and src/lib/session. This check fails when a copy drifts, so a fix made in one console
// is copied to the other. Run from game-ui\: npm run check:shared. Line endings are ignored (Windows checkouts).

import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import { dirname, join, relative, sep } from "node:path";
import { fileURLToPath } from "node:url";

const gameUi = join(dirname(fileURLToPath(import.meta.url)), "..");
const adminUi = join(gameUi, "..", "admin-ui");
const SHARED = ["src/lib/api", "src/lib/session"];

/** Every file under dir, as paths relative to root with "/" ("src/lib/api/client.ts"). */
function filesUnder(root, dir) {
  const start = join(root, dir);
  if (!existsSync(start)) return [];
  const found = [];
  for (const name of readdirSync(start)) {
    const full = join(start, name);
    const rel = relative(root, full).split(sep).join("/");
    if (statSync(full).isDirectory()) found.push(...filesUnder(root, rel));
    else found.push(rel);
  }
  return found;
}

const read = (path) => readFileSync(path, "utf8").replace(/\r\n/g, "\n");

const problems = [];
let compared = 0;
for (const dir of SHARED) {
  const inAdmin = filesUnder(adminUi, dir);
  const inGame = filesUnder(gameUi, dir);
  for (const file of new Set([...inAdmin, ...inGame])) {
    if (!inAdmin.includes(file)) problems.push(`only in game-ui:  ${file}`);
    else if (!inGame.includes(file)) problems.push(`only in admin-ui: ${file}`);
    else if (read(join(adminUi, file)) !== read(join(gameUi, file))) problems.push(`different:        ${file}`);
    else compared++;
  }
}

if (problems.length > 0) {
  console.log(`Shared code has drifted (${problems.length}):`);
  for (const p of problems) console.log(`  ${p}`);
  console.log("Copy the newer file to the other console (both apps must stay identical in these folders).");
  process.exit(1);
}
console.log(`OK: ${compared} shared files are identical in admin-ui and game-ui (${SHARED.join(", ")}).`);

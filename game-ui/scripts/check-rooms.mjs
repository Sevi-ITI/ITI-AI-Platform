// npm run check:rooms (G7): are game-ui's copied pages still the same as admin-ui's? Every copied file is compared
// with its admin-ui original, line by line, after taking out the routine edits every copy gets: comments, blank
// lines, import paths pointing at kit/, <h1> ↔ <h2>, @media ↔ @container page. Any other difference must be listed
// in scripts/rooms-accepted.json with the reason; anything not listed is drift (exit 1). Read-only.
import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import { dirname, join, relative } from "node:path";
import { fileURLToPath } from "node:url";

const GAME = join(dirname(fileURLToPath(import.meta.url)), "..");
const ADMIN = join(GAME, "..", "admin-ui");
const A = (p) => join(ADMIN, "src", "app", p);
const G = (p) => join(GAME, "src", "app", p);

// admin-ui folder or file → game-ui place
const ROOMS = ["performance", "requests", "documents", "chat", "companies", "apps", "users", "accounts", "tools"];
const KIT = [
  "auto-refresh.tsx", "breadcrumbs.tsx", "confirm-action.tsx", "copy-button.tsx", "dashboard.module.css",
  "focus-on-open.tsx", "form-dialog.tsx", "gate-actions.ts", "gate-bar.tsx", "health-cards.tsx", "icons.tsx",
  "pager.tsx", "placeholder.tsx", "toast.tsx", "widgets.tsx",
];
const PAIRS = [
  ["(console)/page.tsx", "(hq)/page.tsx"],
  ["(console)/error.tsx", "(hq)/error.tsx"],
  ["(console)/loading.tsx", "(hq)/loading.tsx"],
  ...KIT.map((f) => [`(console)/${f}`, `(hq)/kit/${f}`]),
  ["api/chat/route.ts", "api/chat/route.ts"],
  ["api/documents/route.ts", "api/documents/route.ts"],
  ["api/health/route.ts", "api/health/route.ts"],
  ["login/login-form.tsx", "login/login-form.tsx"],
  ["login/login.module.css", "login/login.module.css"],
  ["session-ended/route.ts", "session-ended/route.ts"],
];
const files = (dir) =>
  readdirSync(dir).flatMap((name) => {
    const p = join(dir, name);
    return statSync(p).isDirectory() ? files(p) : [p];
  });
for (const room of ROOMS) {
  for (const f of files(A(`(console)/${room}`))) {
    const rel = relative(A(`(console)/${room}`), f);
    PAIRS.push([`(console)/${room}/${rel}`, `(hq)/${room}/${rel}`]);
  }
}
// game-ui's own redesigns: no longer copies, so not compared (their API calls still are: check:parity; their dialogs
// and actions still are, above). Each needs its actions ticked by hand (docs\game-ui\G7-retire-admin-ui-checklist.md).
const REDESIGNED = new Set([
  "(hq)/tools/page.tsx",
  "(hq)/documents/page.tsx",
  "(hq)/apps/page.tsx",
  "(hq)/apps/app-list.tsx",
  "(hq)/companies/page.tsx",
]);
for (let k = PAIRS.length - 1; k >= 0; k--) {
  if (REDESIGNED.has(PAIRS[k][1])) PAIRS.splice(k, 1);
}

// outside src/app
const EXTRA = [[join(ADMIN, "src", "lib", "format.ts"), join(GAME, "src", "lib", "format.ts")]];

function normalize(text, game) {
  const out = [];
  let inBlock = false;
  for (let line of text.replace(/\r\n/g, "\n").split("\n")) {
    if (inBlock) {
      if (line.includes("*/")) {
        inBlock = false;
        line = line.slice(line.indexOf("*/") + 2);
      } else continue;
    }
    line = line.replace(/\/\*.*?\*\//g, ""); // /* … */ on one line
    if (line.includes("/*")) {
      inBlock = true;
      line = line.slice(0, line.indexOf("/*"));
    }
    if (/^\s*\/\//.test(line)) continue; // a // comment line
    line = line.replace(/\s+\/\/ .*$/, ""); // a trailing // comment
    if (game) line = line.replace(/from "((?:\.\.?\/)+)kit\//g, 'from "$1');
    line = line.replace(/<(\/?)h[12]\b/g, "<$1hX").replace(/@container page/g, "@media").trimEnd();
    if (line.trim() !== "") out.push(line);
  }
  return out;
}

// The lines only one side has (an LCS line diff)
function diff(a, b) {
  const m = a.length;
  const n = b.length;
  const dp = Array.from({ length: m + 1 }, () => new Uint32Array(n + 1));
  for (let i = m - 1; i >= 0; i--) {
    for (let j = n - 1; j >= 0; j--) dp[i][j] = a[i] === b[j] ? dp[i + 1][j + 1] + 1 : Math.max(dp[i + 1][j], dp[i][j + 1]);
  }
  const only = [];
  let i = 0;
  let j = 0;
  while (i < m && j < n) {
    if (a[i] === b[j]) {
      i++;
      j++;
    } else if (dp[i + 1][j] >= dp[i][j + 1]) only.push({ side: "admin", text: a[i++].trim() });
    else only.push({ side: "game", text: b[j++].trim() });
  }
  while (i < m) only.push({ side: "admin", text: a[i++].trim() });
  while (j < n) only.push({ side: "game", text: b[j++].trim() });
  return only;
}

const accepted = JSON.parse(readFileSync(join(GAME, "scripts", "rooms-accepted.json"), "utf8"));
const used = new Set();
let drift = 0;
let compared = 0;
const missing = [];
for (const [adminPath, gamePath, label = gamePath] of [
  ...PAIRS.map(([a, g]) => [A(a), G(g), `src/app/${g}`]),
  ...EXTRA.map(([a, g]) => [a, g, relative(GAME, g).replace(/\\/g, "/")]),
]) {
  if (!existsSync(gamePath)) {
    missing.push(label);
    continue;
  }
  compared++;
  const only = diff(normalize(readFileSync(adminPath, "utf8"), false), normalize(readFileSync(gamePath, "utf8"), true));
  const unexplained = only.filter((d) => {
    // each accepted entry explains one line (two identical lines need two entries)
    const k = accepted.findIndex((x, n) => !used.has(n) && x.file === label && x.side === d.side && x.text === d.text);
    if (k >= 0) used.add(k);
    return k < 0;
  });
  if (unexplained.length) {
    drift++;
    console.log(`DRIFT ${label}`);
    for (const d of unexplained) console.log(`  ${d.side === "admin" ? "- only in admin-ui:" : "+ only in game-ui: "} ${d.text}`);
  }
}
const stale = accepted.filter((_, k) => !used.has(k));
for (const s of stale) console.log(`STALE accepted entry (no longer differs): ${s.file} [${s.side}] ${s.text}`);
for (const m of missing) console.log(`MISSING in game-ui: ${m}`);
console.log(
  `${compared} copied files compared with admin-ui; ${drift} with drift, ${missing.length} missing, ${stale.length} stale accepted entries; ${REDESIGNED.size} redesigned pages not compared (${[...REDESIGNED].join(", ")}).`,
);
process.exit(drift || missing.length || stale.length ? 1 : 0);

// The HQ's rooms ("stations"): one per console page, at the same URL as in admin-ui. The 3D scene, the wing dock,
// the list view and the panel header all read this list. Who may enter matches admin-ui's navigation: testers get
// only Chat, the Admin wing is for super admins. Cosmetic only: FastAPI refuses anything a role may not do.

export type Role = "super_admin" | "supervisor" | "tester";

export type WingId = "monitor" | "knowledge" | "clients" | "admin";

export type Station = {
  id: string;
  route: string;
  title: string;
  wing: WingId;
  roomObject: string; // what stands in the room
  desc: string;
  pos: [number, number, number]; // x, height of its label, z
};

export const WINGS: { id: WingId; title: string }[] = [
  { id: "monitor", title: "Monitor · Control Room" },
  { id: "knowledge", title: "Knowledge · Library" },
  { id: "clients", title: "Clients · Embassy" },
  { id: "admin", title: "Admin · Engine Room" },
];

export const STATIONS: Station[] = [
  {
    id: "overview",
    route: "/",
    title: "Overview",
    wing: "monitor",
    roomObject: "Wall of live screens",
    desc: "System health, GPU memory, loaded models, chunks per collection and the latest refused or failed requests.",
    pos: [-7.2, 1.8, -7.2],
  },
  {
    id: "performance",
    route: "/performance",
    title: "Performance",
    wing: "monitor",
    roomObject: "Gauge cluster",
    desc: "Requests and errors over 1 h / 24 h / 7 d, answer times, where the time goes and answer outcomes.",
    pos: [-3.4, 1.8, -7.2],
  },
  {
    id: "requests",
    route: "/requests",
    title: "Request log",
    wing: "monitor",
    roomObject: "Mail chute and ticker tape",
    desc: "Every request: time, app and company, result, time spent and the tools the model ran.",
    pos: [-7.2, 1.8, -3.2],
  },
  {
    id: "documents",
    route: "/documents",
    title: "Documents",
    wing: "knowledge",
    roomObject: "Bookshelves (one per collection)",
    desc: "Collections, who they belong to and are shared with, and every uploaded PDF.",
    pos: [6.8, 2.1, -6.8],
  },
  {
    id: "chat",
    route: "/chat",
    title: "Chat",
    wing: "knowledge",
    roomObject: "Reception desk with the assistant",
    desc: "Ask the company documents: answers with page citations, or \"I don't know\".",
    pos: [3.8, 1.6, -3.5],
  },
  {
    id: "companies",
    route: "/companies",
    title: "Companies",
    wing: "clients",
    roomObject: "Table of building models",
    desc: "Client companies, the apps they connect through and their HR database.",
    pos: [-6.8, 1.6, 4.2],
  },
  {
    id: "apps",
    route: "/apps",
    title: "Apps & keys",
    wing: "clients",
    roomObject: "Key vault",
    desc: "Caller apps, their keys, collections and tools.",
    pos: [-7.2, 2.0, 7.6],
  },
  {
    id: "users",
    route: "/users",
    title: "Users & chats",
    wing: "clients",
    roomObject: "Visitor book",
    desc: "End users of the client apps, their conversations and full transcripts.",
    pos: [-3.4, 1.7, 7.2],
  },
  {
    id: "accounts",
    route: "/accounts",
    title: "Accounts",
    wing: "admin",
    roomObject: "Badge office",
    desc: "Console accounts, their roles and the collections a tester may ask.",
    pos: [3.8, 1.8, 7.2],
  },
  {
    id: "tools",
    route: "/tools",
    title: "Tools & MCP",
    wing: "admin",
    roomObject: "Workshop: MCP pipes and tool valves",
    desc: "Tools the model can use, the records source, MCP connections, SQL tools, Try it and the change log.",
    pos: [7.2, 2.0, 5.2],
  },
  {
    // Outside the building, north of the plaza; not an admin-ui page (V2, Vince: "it is for ME"), super admins only
    id: "clock",
    route: "/clock-tower",
    title: "PHT Clock Tower",
    wing: "monitor",
    roomObject: "Clock tower",
    desc: "Philippine time (Asia/Manila), the sun's phase, the theme that follows the time and a simulated time.",
    pos: [0, 11.6, -23.3], // = CLOCK_POSITION in scene/clock.ts
  },
];

/** May this role open this wing? Same rule as admin-ui's navigation. */
export function canEnterWing(wing: WingId, role: Role): boolean {
  if (role === "tester") return wing === "knowledge";
  if (role === "supervisor") return wing !== "admin";
  return true;
}

/** May this role open this room? Testers: Chat only (not Documents, although it shares their wing). The clock tower:
 *  super admins only. */
export function canEnter(station: Station, role: Role): boolean {
  if (station.id === "clock") return role === "super_admin";
  if (role === "tester") return station.id === "chat";
  return canEnterWing(station.wing, role);
}

/** The room a URL belongs to: "/users/app/user" → Users & chats; "/" only matches Overview exactly. */
export function stationForPath(pathname: string): Station | undefined {
  return STATIONS.find((s) =>
    s.route === "/" ? pathname === "/" : pathname === s.route || pathname.startsWith(`${s.route}/`),
  );
}

import "server-only";

import { callApi } from "@/lib/api/client";
import type { CityBlock } from "@/hq/scene/city";
import type { RoomProps } from "@/hq/scene/props";

// What the 3D HQ shows from real data (super admins' 3D view only):
// - V4 the app city blocks: the real apps (A to Z by id) and the companies each is linked to;
// - the live room props: a bookshelf per collection, a building model per company, a pipe per MCP connection and a
//   valve per tool (state as stored: no server is pinged here, that is the Tools room's Test).
// The same calls the Apps & keys, Companies, Documents and Tools rooms make; only names, counts and on / off reach the
// browser. A failed call just leaves that part empty: the rooms show the error.
export async function loadHq(): Promise<{ city: CityBlock[]; props: RoomProps }> {
  const [apps, companies, collections, connections, tools] = await Promise.all([
    callApi((api) => api.GET("/v1/admin/apps")),
    callApi((api) => api.GET("/v1/admin/companies")),
    callApi((api) => api.GET("/v1/admin/collections")),
    callApi((api) => api.GET("/v1/admin/tools/connections")),
    callApi((api) => api.GET("/v1/admin/tools/tools")),
  ]);
  const companyNames = new Map((companies.ok ? companies.data : []).map((c) => [c.company_id, c.name]));

  const city: CityBlock[] =
    apps.ok && companies.ok
      ? [...apps.data]
          .sort((a, b) => a.app_id.localeCompare(b.app_id))
          .map((app) => ({
            appId: app.app_id,
            name: app.display_name || app.app_id,
            offices: app.company_ids.map((id) => ({ companyId: id, name: companyNames.get(id) ?? id })),
          }))
      : [];

  const props: RoomProps = {
    collections: (collections.ok ? collections.data : []).map((c) => ({ name: c.name, files: c.documents })),
    companies: (companies.ok ? companies.data : []).map((c) => ({ id: c.company_id, name: c.name, activeKeys: c.active_keys })),
    connections: (connections.ok ? connections.data : []).map((c) => ({ name: c.name, usable: c.usable })),
    tools: (tools.ok ? tools.data : []).map((t) => ({
      name: t.name,
      on: t.enabled,
      inUse: t.in_use,
      waiting: t.approval === "pending" || t.approval === "changed",
    })),
  };
  return { city, props };
}

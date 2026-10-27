import "server-only";

import { callApi } from "@/lib/api/client";
import type { CityBlock } from "@/hq/scene/city";

// V4: the app city blocks around the 3D HQ = the real apps (A to Z by id) and the companies each is linked to.
// The same two calls the Apps & keys and Companies rooms make; only names go to the browser (no keys, no counts).
// A failed call just leaves the city empty: the rooms show the error.
export async function loadCity(): Promise<CityBlock[]> {
  const [apps, companies] = await Promise.all([
    callApi((api) => api.GET("/v1/admin/apps")),
    callApi((api) => api.GET("/v1/admin/companies")),
  ]);
  if (!apps.ok || !companies.ok) return [];
  const companyNames = new Map(companies.data.map((c) => [c.company_id, c.name]));
  return [...apps.data]
    .sort((a, b) => a.app_id.localeCompare(b.app_id))
    .map((app) => ({
      appId: app.app_id,
      name: app.display_name || app.app_id,
      offices: app.company_ids.map((id) => ({ companyId: id, name: companyNames.get(id) ?? id })),
    }));
}

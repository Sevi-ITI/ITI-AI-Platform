"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import type { components } from "@/lib/api/schema";

import dash from "../kit/dashboard.module.css";
import FormDialog from "../kit/form-dialog";
import { toast } from "../kit/toast";
import { addCompany, linkApps, saveCompanyDatabase, testCompanyDatabase, updateCompany } from "./actions";

// Add a client company and link it to apps; rename one, change its notes or its linked apps.

export type AppOption = { app_id: string; name: string };

/** Ticks for the apps a company connects to: keys for those apps can then be made for it (Apps & keys). */
function AppChecks({ apps, checked }: { apps: AppOption[]; checked: string[] }) {
  return (
    <fieldset className={dash.checks}>
      <legend>Apps it connects to</legend>
      {apps.length === 0 && <span className={dash.muted}>No apps yet: create one on Apps &amp; keys first.</span>}
      {apps.map((a) => (
        <label key={a.app_id} className={dash.check}>
          <input type="checkbox" name="app_ids" value={a.app_id} defaultChecked={checked.includes(a.app_id)} />
          <span>{a.name}</span>
          {a.name !== a.app_id && <span className={`mono ${dash.muted}`}>({a.app_id})</span>}
        </label>
      ))}
    </fieldset>
  );
}

const text = (data: FormData, name: string) => String(data.get(name) ?? "").trim();

export function AddCompanyButton({ apps }: { apps: AppOption[] }) {
  return (
    <FormDialog
      button="Add company"
      buttonClass={dash.apply}
      title="Add a client company"
      submitLabel="Add company"
      done={(data) => `Company ${text(data, "name")} added`}
      onSubmit={(data) =>
        addCompany({
          company_id: text(data, "company_id"),
          name: text(data, "name"),
          notes: text(data, "notes") || null,
          app_ids: data.getAll("app_ids").map(String),
        })
      }
    >
      <label className={dash.field}>
        <span>Name</span>
        <input name="name" required maxLength={100} placeholder="e.g. Acme Corp…" autoComplete="off" />
      </label>
      <label className={dash.field}>
        <span>Company id (used in keys and collections; can&apos;t be changed later)</span>
        <input
          name="company_id"
          required
          pattern="[a-z0-9\-]{2,64}"
          title="Lowercase letters, digits and hyphens, 2 to 64 characters"
          placeholder="e.g. acme…"
          autoComplete="off"
          spellCheck={false}
        />
      </label>
      <label className={dash.field}>
        <span>Notes (optional)</span>
        <textarea name="notes" rows={2} maxLength={2000} />
      </label>
      <AppChecks apps={apps} checked={[]} />
      <small className={dash.muted}>
        Next: create its collections (Documents → Upload document → New collection), then make each linked app&apos;s
        key inside that app on Apps &amp; keys.
      </small>
    </FormDialog>
  );
}

// --- 8.6M: the company's own database for one system -----------------------------------------------------------

type Database = components["schemas"]["CompanyDatabaseOut"];

/** Set or change where this company's database is: direct (we reach it) or relay (our server runs at the company). */
export function DatabaseDialog({
  companyId,
  system,
  database,
  locked,
}: {
  companyId: string;
  system: string;
  database?: Database;
  locked: boolean;
}) {
  const [mode, setMode] = useState<"direct" | "relay">(database?.mode ?? "direct");
  return (
    <FormDialog
      button={database ? "Edit" : "Set database"}
      buttonClass={dash.smallButton}
      title={`${system} database of ${companyId}`}
      submitLabel="Save"
      locked={locked}
      done={() => `${companyId}: ${system} database saved`}
      onSubmit={(data) =>
        saveCompanyDatabase(companyId, system, {
          mode,
          url_env: mode === "direct" ? text(data, "url_env") : null,
          relay_url: mode === "relay" ? text(data, "relay_url") : null,
          token_env: mode === "relay" ? text(data, "token_env") : null,
          enabled: data.get("enabled") === "on",
        })
      }
    >
      <label className={dash.field}>
        <span>How we reach it</span>
        <select name="mode" value={mode} onChange={(e) => setMode(e.target.value as "direct" | "relay")}>
          <option value="direct">Direct: their database is reachable from the AI server (VPN or allowed IP)</option>
          <option value="relay">Relay: our {system} server runs at the company, next to their database (https)</option>
        </select>
      </label>
      {mode === "direct" ? (
        <label className={dash.field}>
          <span>Database address: the NAME of its variable in backend\.env (the address stays there)</span>
          <input
            name="url_env"
            required
            pattern="ITI_[A-Z0-9_]+"
            defaultValue={database?.url_env ?? ""}
            placeholder={`ITI_DB_${companyId.toUpperCase().replace(/-/g, "_")}_${system.toUpperCase()}…`}
            autoComplete="off"
            spellCheck={false}
          />
        </label>
      ) : (
        <>
          <label className={dash.field}>
            <span>URL of our server at the company</span>
            <input
              name="relay_url"
              required
              defaultValue={database?.relay_url ?? ""}
              placeholder="https://hr-ai.company.com/mcp…"
              autoComplete="off"
              spellCheck={false}
            />
          </label>
          <label className={dash.field}>
            <span>Secret: the NAME of its variable in backend\.env (the secret itself stays there)</span>
            <input
              name="token_env"
              required
              pattern="ITI_MCP_[A-Z0-9_]+"
              defaultValue={database?.token_env ?? ""}
              placeholder={`ITI_MCP_${companyId.toUpperCase().replace(/-/g, "_")}_TOKEN…`}
              autoComplete="off"
              spellCheck={false}
            />
          </label>
        </>
      )}
      <label className={dash.check}>
        <input type="checkbox" name="enabled" defaultChecked={database?.enabled ?? true} />
        <span>Enabled (off = the company gets none of the {system} tools)</span>
      </label>
    </FormDialog>
  );
}

export function DatabaseTestButton({ companyId, system }: { companyId: string; system: string }) {
  const [busy, setBusy] = useState(false);
  const router = useRouter();
  return (
    <button
      type="button"
      className={dash.smallButton}
      disabled={busy}
      aria-busy={busy}
      onClick={async () => {
        setBusy(true);
        const r = await testCompanyDatabase(companyId, system);
        setBusy(false);
        if (!r.ok) return r.status === 401 ? router.push("/login") : toast("error", r.message);
        const t = r.test;
        const db = t.database; // direct: did the login answer; relay: did our server there list its tools
        if (db) toast(db.reachable ? "ok" : "error", db.reachable ? `${system}: database ${db.database} reachable` : `${system}: database not reachable (${db.error})`);
        else toast(t.ok ? "ok" : "error", t.ok ? `${system}: relay answered with ${t.tools.length} tools in ${t.seconds} s` : `${system}: relay did not answer (${t.error})`);
      }}
    >
      {busy ? "Testing…" : "Test"}
    </button>
  );
}

export function EditCompanyButton({
  companyId,
  name,
  notes,
  apps,
  linked,
}: {
  companyId: string;
  name: string;
  notes: string | null;
  apps: AppOption[];
  linked: string[];
}) {
  return (
    <FormDialog
      button="Edit"
      buttonClass={dash.smallButton}
      title={`Edit ${companyId}`}
      submitLabel="Save"
      done={(data) => `${text(data, "name")} saved`}
      onSubmit={async (data) => {
        // links first: an app that still has an active key here can't be unlinked, and then nothing is saved
        const links = await linkApps(companyId, data.getAll("app_ids").map(String));
        if (!links.ok) return links;
        return updateCompany(companyId, { name: text(data, "name"), notes: text(data, "notes") || null });
      }}
    >
      <label className={dash.field}>
        <span>Name</span>
        <input name="name" required maxLength={100} defaultValue={name} autoComplete="off" />
      </label>
      <label className={dash.field}>
        <span>Notes</span>
        <textarea name="notes" rows={2} maxLength={2000} defaultValue={notes ?? ""} />
      </label>
      <AppChecks apps={apps} checked={linked} />
    </FormDialog>
  );
}

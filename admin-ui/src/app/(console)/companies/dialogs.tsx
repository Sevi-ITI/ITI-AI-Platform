"use client";

import dash from "../dashboard.module.css";
import FormDialog from "../form-dialog";
import { addCompany, linkApps, updateCompany } from "./actions";

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

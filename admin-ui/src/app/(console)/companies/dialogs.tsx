"use client";

import dash from "../dashboard.module.css";
import FormDialog from "../form-dialog";
import { addCompany, updateCompany } from "./actions";

// Add a client company; rename one or change its notes.

const text = (data: FormData, name: string) => String(data.get(name) ?? "").trim();

export function AddCompanyButton() {
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
      <small className={dash.muted}>
        Next: create its collections (Documents → Upload document → New collection) and its keys (Apps &amp; keys).
      </small>
    </FormDialog>
  );
}

export function EditCompanyButton({
  companyId,
  name,
  notes,
}: {
  companyId: string;
  name: string;
  notes: string | null;
}) {
  return (
    <FormDialog
      button="Edit"
      buttonClass={dash.smallButton}
      title={`Edit ${companyId}`}
      submitLabel="Save"
      done={(data) => `${text(data, "name")} saved`}
      onSubmit={(data) => updateCompany(companyId, { name: text(data, "name"), notes: text(data, "notes") || null })}
    >
      <label className={dash.field}>
        <span>Name</span>
        <input name="name" required maxLength={100} defaultValue={name} autoComplete="off" />
      </label>
      <label className={dash.field}>
        <span>Notes</span>
        <textarea name="notes" rows={2} maxLength={2000} defaultValue={notes ?? ""} />
      </label>
    </FormDialog>
  );
}

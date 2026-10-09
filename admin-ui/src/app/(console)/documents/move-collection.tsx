"use client";

import dash from "../dashboard.module.css";
import FormDialog from "../form-dialog";
import { moveCollection } from "./actions";

// "Move…" on a collection: give it to another company, or make it Global (e.g. labor law for every client).

const GLOBAL = "__global__";

export default function MoveCollectionButton({
  name,
  current,
  companies,
}: {
  name: string;
  current: string | null;
  companies: { company_id: string; name: string }[];
}) {
  const owner = (data: FormData) => {
    const v = String(data.get("company") ?? GLOBAL);
    return v === GLOBAL ? null : v;
  };
  const label = (id: string | null) => (id ? (companies.find((c) => c.company_id === id)?.name ?? id) : "Global");

  return (
    <FormDialog
      button="Move…"
      buttonClass={dash.smallButton}
      title={`Move ${name}`}
      submitLabel="Move collection"
      done={(data) => `${name} now belongs to ${label(owner(data))}`}
      onSubmit={(data) => moveCollection(name, owner(data))}
    >
      <label className={dash.field}>
        <span>Belongs to</span>
        <select name="company" defaultValue={current ?? GLOBAL}>
          {companies.map((c) => (
            <option key={c.company_id} value={c.company_id}>
              {c.name} ({c.company_id})
            </option>
          ))}
          <option value={GLOBAL}>Global: every company may be given it</option>
        </select>
      </label>
      <small className={dash.muted}>
        Moving it to a company is refused while another company&apos;s active key uses it (take it off that key first).
        Making it Global is always allowed; keys still get it only when you add it to them.
      </small>
    </FormDialog>
  );
}

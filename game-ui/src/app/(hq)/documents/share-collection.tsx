"use client";

import dash from "../kit/dashboard.module.css";
import FormDialog from "../kit/form-dialog";
import { shareCollection } from "./actions";

// "Share…" on a company's collection: tick the other companies whose keys may also be given it. It still reaches
// a company only through a key you add it to. (Global collections have no Share…: every company may use them.)

export default function ShareCollectionButton({
  name,
  owner,
  sharedWith,
  companies,
}: {
  name: string;
  owner: string;
  sharedWith: string[];
  companies: { company_id: string; name: string }[];
}) {
  const others = companies.filter((c) => c.company_id !== owner);
  const picked = (data: FormData) => data.getAll("company").map(String);
  const label = (id: string) => companies.find((c) => c.company_id === id)?.name ?? id;

  return (
    <FormDialog
      button="Share…"
      buttonClass={dash.smallButton}
      title={`Share ${name}`}
      submitLabel="Save sharing"
      done={(data) => {
        const ids = picked(data);
        return ids.length ? `${name} is shared with ${ids.map(label).join(", ")}` : `${name} is no longer shared`;
      }}
      onSubmit={(data) => shareCollection(name, picked(data))}
    >
      <fieldset className={dash.checks}>
        <legend>Also shared with (besides its owner, {label(owner)})</legend>
        {others.length === 0 && <span className={dash.muted}>There are no other companies yet.</span>}
        {others.map((c) => (
          <label key={c.company_id} className={dash.check}>
            <input
              type="checkbox"
              name="company"
              value={c.company_id}
              defaultChecked={sharedWith.includes(c.company_id)}
            />
            <span>{c.name}</span>
            <span className={`mono ${dash.muted}`} translate="no">
              {c.company_id}
            </span>
          </label>
        ))}
      </fieldset>
      <small className={dash.muted}>
        A shared company&apos;s keys may be given this collection; they get it only when you add it to a key. Unticking
        a company is refused while one of its active keys still uses the collection (take it off that key first).
      </small>
    </FormDialog>
  );
}

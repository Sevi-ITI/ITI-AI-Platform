"use client";

import dash from "./dashboard.module.css";
import { CopyIcon } from "./icons";
import { toast } from "./toast";

// A small "Copy" button for an id (request id, key id...). The value is already on the page; this only saves
// selecting it by hand. The toast confirms it (screen readers hear the toast).
export default function CopyButton({ value, label }: { value: string; label: string }) {
  return (
    <button
      type="button"
      className={dash.copyButton}
      aria-label={`Copy ${label}`}
      onClick={() =>
        void navigator.clipboard.writeText(value).then(
          () => toast("ok", `${label} copied`),
          () => toast("error", `Couldn't copy the ${label}; select it by hand`),
        )
      }
    >
      <CopyIcon /> Copy
    </button>
  );
}

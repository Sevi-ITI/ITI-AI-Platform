"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import type { components } from "@/lib/api/schema";

import dash from "./dashboard.module.css";
import FormDialog from "./form-dialog";
import { LockIcon, StatusWarnIcon, UnlockIcon } from "./icons";
import { toast } from "./toast";
import { lockGate, unlockGate } from "./gate-actions";

// 8.6e-3: the security password gate, under the page title of Tools & MCP and Apps & keys (super admins only).
// A second password, separate from the login, set ONLY on the server (python -m scripts.set_security_password).
// Unlocked = the risky changes (marked with a padlock while locked) are open for 15 minutes from the unlock.
// FastAPI decides; this bar only shows the state and refreshes the page when the 15 minutes are over.

type Gate = components["schemas"]["GateOut"];

const hhmm = new Intl.DateTimeFormat("en-PH", { timeZone: "Asia/Manila", hour: "2-digit", minute: "2-digit", hourCycle: "h23" });
const at = (value: string) => hhmm.format(new Date(value));

export default function GateBar({ gate }: { gate: Gate }) {
  const router = useRouter();
  const [minutesLeft, setMinutesLeft] = useState<number | null>(null); // set after the page is in the browser
  const [busy, setBusy] = useState(false);
  const until = gate.unlocked_until ?? gate.locked_until;

  useEffect(() => {
    if (!until) return;
    const tick = () => {
      const left = Date.parse(until) - Date.now();
      if (left <= 0) return router.refresh(); // over: the page comes back locked (or no longer locked out)
      setMinutesLeft(Math.ceil(left / 60_000));
    };
    tick();
    const timer = window.setInterval(tick, 15_000);
    return () => window.clearInterval(timer);
  }, [until, router]);

  const left = minutesLeft === null ? "" : ` (${minutesLeft} min left)`;

  if (!gate.password_set) {
    return (
      <div className={dash.gateBar}>
        <p>
          <LockIcon />
          <span>
            Changes marked with a padlock need a security password, and none is set yet. Set it on the server, from{" "}
            <span className="mono">backend\</span>: <span className="mono">python -m scripts.set_security_password &lt;your username&gt;</span>
          </span>
        </p>
      </div>
    );
  }

  if (gate.locked_until) {
    return (
      <div className={dash.gateBar}>
        <p className={dash.warn}>
          <StatusWarnIcon />
          <span>
            Locked after 5 wrong security passwords, until {at(gate.locked_until)}
            {left}. Your console login still works.
          </span>
        </p>
      </div>
    );
  }

  if (gate.unlocked_until) {
    return (
      <div className={`${dash.gateBar} ${dash.gateOpen}`}>
        <p>
          <UnlockIcon />
          <span>
            Unlocked until {at(gate.unlocked_until)}
            {left}: the changes marked with a padlock are open.
          </span>
        </p>
        <div className={dash.gateActions}>
          <button
            type="button"
            className={dash.smallButton}
            disabled={busy}
            aria-busy={busy}
            onClick={async () => {
              setBusy(true);
              const r = await lockGate();
              setBusy(false);
              if (r.ok) {
                toast("ok", "Locked");
                router.refresh();
              } else if (r.status === 401) {
                router.push("/login");
              } else {
                toast("error", r.message);
              }
            }}
          >
            Lock now
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className={dash.gateBar}>
      <p>
        <LockIcon />
        <span>Locked: the changes marked with a padlock need your security password (it unlocks them for 15 minutes).</span>
      </p>
      <div className={dash.gateActions}>
        <FormDialog
          button="Unlock"
          buttonClass={dash.apply}
          title="Unlock with your security password"
          submitLabel="Unlock"
          done={() => "Unlocked for 15 minutes"}
          onSubmit={(data) => unlockGate(String(data.get("password") ?? ""))}
        >
          <p className={dash.muted}>
            Your second password, not the login one. 5 wrong in a row lock it for 15 minutes. Every unlock is logged.
          </p>
          <label className={dash.field}>
            <span>Security password</span>
            <input name="password" type="password" required maxLength={200} autoComplete="off" spellCheck={false} />
          </label>
        </FormDialog>
      </div>
    </div>
  );
}

"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import type { components } from "@/lib/api/schema";

import dash from "../dashboard.module.css";
import FormDialog from "../form-dialog";
import { toast } from "../toast";
import {
  checkSqlTool,
  saveConnection,
  saveSqlTool,
  setRecordsSource,
  setToolDescription,
  setToolEnabled,
  testConnection,
} from "./actions";

// The Tools & MCP page's buttons and dialogs. Every change goes to FastAPI (super admin only, logged); a 401 means
// the session is over. Secrets are never typed here: a connection names the backend\.env variable that holds one.

type Connection = components["schemas"]["ConnectionOut"];
type SqlTool = components["schemas"]["SqlToolOut"];
type Failure = { ok: false; message: string; status: number };

function useAfter() {
  const router = useRouter();
  return (r: { ok: true } | Failure, done: string) => {
    if (r.ok) {
      toast("ok", done);
      router.refresh();
    } else if (r.status === 401) {
      router.push("/login");
    } else {
      toast("error", r.message);
    }
  };
}

const lines = (value: FormDataEntryValue | null) =>
  String(value ?? "")
    .split(/[\n,]/)
    .map((t) => t.trim())
    .filter(Boolean);

// --- records source -----------------------------------------------------------------------------------------

export function RecordsSourceSwitch({ current, dbConfigured }: { current: "builtin" | "mcp"; dbConfigured: boolean }) {
  const after = useAfter();
  const [busy, setBusy] = useState(false);
  const choose = async (source: "builtin" | "mcp") => {
    if (source === current || busy) return;
    setBusy(true);
    after(await setRecordsSource(source), source === "mcp" ? "Records now answered by the records MCP server" : "Records now answered by the built-in tools");
    setBusy(false);
  };
  return (
    <>
      {/* a block wrapper: the switch keeps its own width instead of stretching across the card */}
      <div>
        <div className={dash.switch} role="group" aria-label="Who answers records questions">
        {(["builtin", "mcp"] as const).map((source) => (
          <button key={source} type="button" aria-pressed={current === source} disabled={busy} onClick={() => void choose(source)}>
            {source === "builtin" ? "Built-in tools" : "Records MCP server"}
          </button>
        ))}
        </div>
      </div>
      {current === "builtin" && !dbConfigured && (
        <p className={dash.warn}>The records DB is not configured (ITI_RECORDS_DB_URL), so the built-in tools are off.</p>
      )}
    </>
  );
}

// --- connections --------------------------------------------------------------------------------------------

export function ConnectionDialog({ connection, stdioServers }: { connection?: Connection; stdioServers: string[] }) {
  const [transport, setTransport] = useState<"stdio" | "http">(connection?.transport ?? "stdio");
  const editing = Boolean(connection);
  return (
    <FormDialog
      button={editing ? "Edit" : "Add connection"}
      buttonClass={editing ? dash.smallButton : dash.apply}
      title={editing ? `Edit ${connection!.name}` : "Add an MCP connection"}
      submitLabel="Save"
      done={(data) => `Connection ${editing ? connection!.name : String(data.get("name") ?? "")} saved`}
      onSubmit={(data) => {
        const name = editing ? connection!.name : String(data.get("name") ?? "").trim();
        const http = data.get("transport") === "http";
        return saveConnection(name, {
          transport: http ? "http" : "stdio",
          server: http ? null : String(data.get("server") ?? ""),
          url: http ? String(data.get("url") ?? "").trim() : null,
          token_env: http ? String(data.get("token_env") ?? "").trim() : null,
          scope: String(data.get("scope") ?? "").trim(),
          topics: lines(data.get("topics")),
          records: data.get("records") === "on",
          enabled: data.get("enabled") === "on",
        });
      }}
    >
      {!editing && (
        <label className={dash.field}>
          <span>Name (tools become name__tool)</span>
          <input name="name" required pattern="[a-z][a-z0-9_]{1,30}" placeholder="e.g. payroll…" autoComplete="off" spellCheck={false} />
        </label>
      )}
      <label className={dash.field}>
        <span>How to reach it</span>
        <select name="transport" value={transport} onChange={(e) => setTransport(e.target.value as "stdio" | "http")}>
          <option value="stdio">stdio: a server on this machine (defined in mcp_servers.py), started by the AI host</option>
          <option value="http">http: a server on another machine (https unless 127.0.0.1)</option>
        </select>
      </label>
      {transport === "stdio" ? (
        <label className={dash.field}>
          <span>Server</span>
          <select name="server" defaultValue={connection?.server ?? stdioServers[0]}>
            {stdioServers.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </label>
      ) : (
        <>
          <label className={dash.field}>
            <span>URL</span>
            <input name="url" required defaultValue={connection?.url ?? ""} placeholder="https://payroll-mcp.iti.local/mcp…" autoComplete="off" spellCheck={false} />
          </label>
          <label className={dash.field}>
            <span>Secret: the NAME of its variable in backend\.env (the secret itself stays there)</span>
            <input name="token_env" required pattern="ITI_MCP_[A-Z0-9_]+" defaultValue={connection?.token_env ?? ""} placeholder="ITI_MCP_PAYROLL_TOKEN…" autoComplete="off" spellCheck={false} />
          </label>
        </>
      )}
      <label className={dash.field}>
        <span>Key scope needed to use its tools</span>
        <input name="scope" required defaultValue={connection?.scope ?? "records:read"} autoComplete="off" spellCheck={false} />
      </label>
      <label className={dash.field}>
        <span>Topics (what it answers, for the model; one per line)</span>
        <textarea name="topics" required rows={3} defaultValue={(connection?.topics ?? []).join("\n")} placeholder="payroll…" />
      </label>
      <label className={dash.check}>
        <input type="checkbox" name="records" defaultChecked={connection?.records ?? false} />
        <span>It answers the records questions (used only while the records source is “Records MCP server”)</span>
      </label>
      <label className={dash.check}>
        <input type="checkbox" name="enabled" defaultChecked={connection?.enabled ?? true} />
        <span>Enabled</span>
      </label>
    </FormDialog>
  );
}

export function TestButton({ name }: { name: string }) {
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
        const r = await testConnection(name);
        setBusy(false);
        if (!r.ok) return r.status === 401 ? router.push("/login") : toast("error", r.message);
        const t = r.test;
        toast(t.ok ? "ok" : "error", t.ok ? `${name}: ${t.tools.length} tools in ${t.seconds} s` : `${name} did not answer (${t.error})`);
      }}
    >
      {busy ? "Testing…" : "Test"}
    </button>
  );
}

// --- tools --------------------------------------------------------------------------------------------------

export function ToolSwitch({ name, enabled }: { name: string; enabled: boolean }) {
  const after = useAfter();
  const [busy, setBusy] = useState(false);
  return (
    <label className={dash.check}>
      <input
        type="checkbox"
        checked={enabled}
        disabled={busy}
        aria-label={`${name} on`}
        onChange={async (e) => {
          setBusy(true);
          after(await setToolEnabled(name, e.target.checked), `${name} ${e.target.checked ? "switched on" : "switched off"}`);
          setBusy(false);
        }}
      />
      <span>{enabled ? "On" : "Off"}</span>
    </label>
  );
}

export function DescriptionDialog({ name, description, codeDescription, changed }: { name: string; description: string; codeDescription: string; changed: boolean }) {
  return (
    <FormDialog
      button="Edit text"
      buttonClass={dash.smallButton}
      title={`What the model reads for ${name}`}
      submitLabel="Save"
      done={(data) => (data.get("reset") === "on" ? `${name}: back to the code's text` : `${name}: text saved`)}
      onSubmit={(data) =>
        setToolDescription(name, data.get("reset") === "on" ? null : String(data.get("description") ?? "").trim())
      }
    >
      <p className={dash.warn}>
        The model picks tools by this text. Say “the CURRENT USER&apos;s own …” and what it is NOT for; re-run the live
        check (scripts/check_records_chat) after a change.
      </p>
      <label className={dash.field}>
        <span>Text</span>
        <textarea name="description" rows={5} maxLength={1000} defaultValue={description} />
      </label>
      {changed && (
        <label className={dash.check}>
          <input type="checkbox" name="reset" />
          <span>Back to the code&apos;s text: “{codeDescription}”</span>
        </label>
      )}
    </FormDialog>
  );
}

// --- SQL tools ----------------------------------------------------------------------------------------------

type Parameter = components["schemas"]["SqlParameter"];

const parseParameters = (value: string): Parameter[] =>
  value
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      // name | string, integer or date | description | required
      const [name, type, description, required] = line.split("|").map((part) => part.trim());
      return { name, type: (type || "string") as Parameter["type"], description: description ?? "", required: required === "required" };
    });

const formatParameters = (parameters: Parameter[]) =>
  parameters.map((p) => [p.name, p.type, p.description ?? "", p.required ? "required" : ""].join(" | ")).join("\n");

export function SqlToolDialog({ tool }: { tool?: SqlTool }) {
  const editing = Boolean(tool);
  const [checkResult, setCheckResult] = useState<string | null>(null);
  const bodyOf = (data: FormData) => ({
    description: String(data.get("description") ?? "").trim(),
    sql: String(data.get("sql") ?? "").trim(),
    parameters: parseParameters(String(data.get("parameters") ?? "")),
    scope: String(data.get("scope") ?? "records:read").trim(),
    topic: String(data.get("topic") ?? "").trim(),
    enabled: data.get("enabled") === "on",
  });
  return (
    <FormDialog
      button={editing ? "Edit" : "Add SQL tool"}
      buttonClass={editing ? dash.smallButton : dash.apply}
      title={editing ? `Edit ${tool!.name}` : "Add a SQL tool"}
      submitLabel="Check and save"
      done={(data) => `SQL tool ${editing ? tool!.name : String(data.get("name") ?? "")} saved`}
      onSubmit={async (data) => {
        const name = editing ? tool!.name : String(data.get("name") ?? "").trim();
        const body = bodyOf(data);
        const checked = await checkSqlTool(name, body);
        if (!checked.ok) return checked;
        if (!checked.check.ok) return checked.check.problems.join(" · ");
        setCheckResult(`Columns: ${checked.check.columns.join(", ")}`);
        return saveSqlTool(name, body);
      }}
    >
      <p className={dash.warn}>
        One SELECT on ai.* views only, with WHERE employee_id = :employee_id (the asking employee, always from the app).
        It runs with the read-only records login. Saving first runs it once as an employee that does not exist.
      </p>
      {!editing && (
        <label className={dash.field}>
          <span>Name</span>
          <input name="name" required pattern="[a-z][a-z0-9_]{2,40}" placeholder="e.g. get_my_overtime…" autoComplete="off" spellCheck={false} />
        </label>
      )}
      <label className={dash.field}>
        <span>Description (what the model reads)</span>
        <textarea name="description" required rows={3} defaultValue={tool?.description ?? "Get the CURRENT USER's own …"} />
      </label>
      <label className={dash.field}>
        <span>SQL</span>
        <textarea name="sql" required rows={6} className="mono" spellCheck={false} defaultValue={tool?.sql ?? "SELECT … FROM ai.… WHERE employee_id = :employee_id"} />
      </label>
      <label className={dash.field}>
        <span>Arguments, one per line: name | string, integer or date | description | required</span>
        <textarea name="parameters" rows={3} className="mono" spellCheck={false} defaultValue={formatParameters(tool?.parameters ?? [])} placeholder="year | integer | Calendar year | required" />
      </label>
      <label className={dash.field}>
        <span>Topic (a few words for the model)</span>
        <input name="topic" required defaultValue={tool?.topic ?? ""} placeholder="overtime…" />
      </label>
      <label className={dash.field}>
        <span>Key scope</span>
        <input name="scope" required defaultValue={tool?.scope ?? "records:read"} spellCheck={false} />
      </label>
      <label className={dash.check}>
        <input type="checkbox" name="enabled" defaultChecked={tool?.enabled ?? true} />
        <span>Enabled</span>
      </label>
      {checkResult && <p className={dash.muted}>{checkResult}</p>}
    </FormDialog>
  );
}

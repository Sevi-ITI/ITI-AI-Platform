"use client";

import { useRouter } from "next/navigation";
import { useRef, useState } from "react";

import type { components } from "@/lib/api/schema";

import dash from "../dashboard.module.css";
import FormDialog, { LOCKED_HINT } from "../form-dialog";
import { LockIcon, StatusOkIcon, StatusWarnIcon } from "../icons";
import { toast } from "../toast";
import {
  checkSqlTool,
  getToolCode,
  saveConnection,
  saveSqlTool,
  setRecordsSource,
  setToolDescription,
  setToolEnabled,
  testConnection,
  tryTools,
  type ToolCode,
  type TryOut,
} from "./actions";

// The Tools & MCP page's buttons and dialogs. Every change goes to FastAPI (super admin only, logged); a 401 means
// the session is over. Secrets are never typed here: a connection names the backend\.env variable that holds one.
// `locked` (8.6e-3): the risky ones are greyed out with a padlock until the security password is unlocked (the gate
// bar at the top of the page); FastAPI refuses them anyway.

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

export function ConnectionDialog({ connection, stdioServers, locked }: { connection?: Connection; stdioServers: string[]; locked: boolean }) {
  const [transport, setTransport] = useState<"stdio" | "http">(connection?.transport ?? "stdio");
  const editing = Boolean(connection);
  return (
    <FormDialog
      button={editing ? "Edit" : "Add connection"}
      buttonClass={editing ? dash.smallButton : dash.apply}
      title={editing ? `Edit ${connection!.name}` : "Add an MCP connection"}
      submitLabel="Save"
      locked={locked}
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
        const db = t.database; // our servers that read a database: did its login answer too?
        const dbNote = !db ? "" : db.reachable ? `; database ${db.database} reachable` : `; database not reachable (${db.error})`;
        const good = t.ok && (!db || db.reachable);
        toast(good ? "ok" : "error", t.ok ? `${name}: ${t.tools.length} tools in ${t.seconds} s${dbNote}` : `${name} did not answer (${t.error})${dbNote}`);
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

export function DescriptionDialog({ name, description, codeDescription, changed, locked }: { name: string; description: string; codeDescription: string; changed: boolean; locked: boolean }) {
  return (
    <FormDialog
      button="Edit text"
      buttonClass={dash.smallButton}
      title={`What the model reads for ${name}`}
      submitLabel="Save"
      locked={locked}
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

// 8.6e-3: what a tool really runs, read only (no editing in the browser: that would be remote code execution).
// Fetched when opened, so every view is a row in the change log.
const CODE_KIND = { "built-in": "its section of tools.py", sql: "its SQL", mcp: "as its MCP server describes it" } as const;

export function CodeButton({ name, locked }: { name: string; locked: boolean }) {
  const router = useRouter();
  const dialog = useRef<HTMLDialogElement>(null);
  const [busy, setBusy] = useState(false);
  const [code, setCode] = useState<ToolCode | null>(null);
  return (
    <>
      <button
        type="button"
        className={locked ? `${dash.smallButton} ${dash.lockedButton}` : dash.smallButton}
        disabled={busy || locked}
        aria-busy={busy}
        title={locked ? LOCKED_HINT : undefined}
        onClick={async () => {
          setBusy(true);
          const r = await getToolCode(name);
          setBusy(false);
          if (r.ok) {
            setCode(r.code);
            dialog.current?.showModal();
            router.refresh(); // the Changes card shows the code.view row
          } else if (r.status === 401) {
            router.push("/login");
          } else {
            toast("error", r.message);
          }
        }}
      >
        {locked && <LockIcon />}
        {busy ? "Opening…" : "View code"}
      </button>
      <dialog ref={dialog} className={`${dash.dialog} ${dash.codeDialog}`} aria-label={`Code of ${name}`}>
        <form method="dialog" className={dash.dialogForm}>
          <h2>
            <span className="mono" translate="no">
              {name}
            </span>
            : {code ? CODE_KIND[code.kind] : ""} (read only)
          </h2>
          <pre className={dash.codeView} tabIndex={0} aria-label={`Code of ${name}`} translate="no">
            {code?.code}
          </pre>
          <div className={dash.dialogActions}>
            <button type="submit" className={dash.secondary}>
              Close
            </button>
          </div>
        </form>
      </dialog>
    </>
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

export function SqlToolDialog({ tool, locked }: { tool?: SqlTool; locked: boolean }) {
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
      locked={locked}
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

// --- Try it -------------------------------------------------------------------------------------------------

// One question as a test employee ID with the ticked tool scopes, through the real chat's tool loop (switch "try_it").
// It reads REAL records: FastAPI allows super admins only and logs every use (never the question or the answer).
export function TryItPanel({ scopes, locked }: { scopes: string[]; locked: boolean }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<TryOut | null>(null);
  const [problem, setProblem] = useState<string | null>(null);

  const ask = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const data = new FormData(e.currentTarget);
    const chosen = data.getAll("scopes").map(String);
    if (chosen.length === 0) return setProblem("Tick at least one tool scope.");
    setBusy(true);
    setProblem(null);
    setResult(null);
    const r = await tryTools({
      scopes: chosen,
      test_user_id: String(data.get("test_user_id") ?? "").trim(),
      question: String(data.get("question") ?? "").trim(),
    });
    setBusy(false);
    if (r.ok) {
      setResult(r.result);
      router.refresh(); // the Changes card shows the new try_it row
    } else if (r.status === 401) {
      router.push("/login");
    } else {
      setProblem(r.message);
    }
  };

  if (scopes.length === 0) {
    return <p className={dash.muted}>No tool scopes yet: add a tool or an MCP connection first.</p>;
  }
  return (
    <>
      <p className={dash.warn}>
        This acts as a REAL employee and reads their real records. Every use is logged (who, test ID, scopes, tools that
        ran); the question and the answer are not.
      </p>
      <form className={dash.tryForm} onSubmit={(e) => void ask(e)}>
        <fieldset className={dash.checks}>
          <legend>Tool scopes to test with</legend>
          {scopes.map((s) => (
            <label key={s} className={dash.check}>
              <input type="checkbox" name="scopes" value={s} />
              <span className="mono">{s}</span>
            </label>
          ))}
        </fieldset>
        <label className={dash.field}>
          <span>Test user ID (stands in for the ITI-User-Id header)</span>
          <input name="test_user_id" required maxLength={100} className="mono" placeholder="e.g. 10…" autoComplete="off" spellCheck={false} />
        </label>
        <label className={dash.field}>
          <span>Question</span>
          <textarea name="question" required rows={2} maxLength={4000} placeholder="How many vacation days do I have left?…" />
        </label>
        <div>
          <button
            type="submit"
            className={locked ? `${dash.apply} ${dash.lockedButton}` : dash.apply}
            disabled={busy || locked}
            aria-busy={busy}
            title={locked ? LOCKED_HINT : undefined}
          >
            {locked && <LockIcon />}
            {busy ? "Asking…" : "Ask"}
          </button>
        </div>
      </form>
      <div aria-live="polite">
        {problem && (
          <p className={dash.error} role="alert">
            {problem}
          </p>
        )}
        {result && <TryResult result={result} />}
      </div>
    </>
  );
}

function TryResult({ result }: { result: TryOut }) {
  return (
    <div className={dash.tryResult}>
      {result.documents_question ? (
        <p className={dash.muted}>
          No tool used: in the real chat this question goes to the company documents (RAG). Try it tests tools only.
          {result.offered.length === 0 && " No tool was offered with these scopes (connection off, records DB not set, or tool switched off)."}
        </p>
      ) : (
        <p className={dash.tryAnswer}>{result.answer}</p>
      )}
      <dl className={dash.facts}>
        <div>
          <dt>Time</dt>
          <dd>{result.seconds} s</dd>
        </div>
        <div>
          <dt>Data found</dt>
          <dd>{result.found ? "yes" : "no"}</dd>
        </div>
        <div>
          <dt>Offered</dt>
          <dd className={`mono ${dash.wrapAnywhere}`}>{result.offered.join(", ") || "none"}</dd>
        </div>
      </dl>
      {result.calls.length > 0 && (
        <div className={dash.tableWrap}>
          <table className={dash.table}>
            <thead>
              <tr>
                <th scope="col">Tool called</th>
                <th scope="col">Arguments</th>
                <th scope="col">Time</th>
                <th scope="col">Result</th>
              </tr>
            </thead>
            <tbody>
              {result.calls.map((c, i) => (
                <tr key={i}>
                  <td className={`mono ${dash.nowrap}`} translate="no">
                    {c.tool}
                  </td>
                  <td className={`mono ${dash.wrapAnywhere}`}>
                    {Object.keys(c.arguments).length ? JSON.stringify(c.arguments) : "–"}
                  </td>
                  <td className={dash.nowrap}>{c.ms} ms</td>
                  <td className={dash.nowrap}>
                    {c.error ? (
                      <span className={`${dash.withIcon} ${dash.error}`}>
                        <StatusWarnIcon /> {c.error}
                      </span>
                    ) : (
                      <span className={`${dash.withIcon} ${dash.ok}`}>
                        <StatusOkIcon /> worked
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {result.sources.length > 0 && (
        <p className={dash.kpiNote}>Sources: {result.sources.map((s) => s.title).join(" · ")}</p>
      )}
    </div>
  );
}

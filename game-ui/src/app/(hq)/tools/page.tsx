// Tools & MCP, redesigned for game-ui (Vince, 2026-10-27: "simply give a very brief description of each tool and add a
// dropdown for the list of tools of each MCP connection"). Not a copy of admin-ui's page any more: the same FastAPI
// calls (check:parity), the same dialogs and actions (controls.tsx, actions.ts: copies, check:rooms), a new layout:
// one card per source (built-in tools by system, each MCP connection, SQL tools), its tools folded under it, one line
// each with a brief description (the first sentence of what the model reads; the full text is in Description).
import { displayMessage } from "@/lib/api/api-error";
import { callApi, endSessionOn401 } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";
import { formatDateTime } from "@/lib/format";
import { currentAccount } from "@/lib/session/current-account";
import { testersGoToChat } from "@/lib/session/testers-go-to-chat";

import ConfirmAction from "../kit/confirm-action";
import styles from "../kit/dashboard.module.css";
import GateBar from "../kit/gate-bar";
import Placeholder from "../kit/placeholder";
import { StatusOkIcon, StatusWarnIcon } from "../kit/icons";
import { Problem } from "../kit/widgets";
import { approveTool, deleteConnection, deleteSqlTool } from "./actions";
import {
  CodeButton,
  ConnectionDialog,
  DescriptionDialog,
  RecordsSourceSwitch,
  SqlToolDialog,
  TestButton,
  ToolSwitch,
  TryItPanel,
} from "./controls";
import css from "./tools.module.css";

export const metadata = { title: "Tools & MCP" };

type Tool = components["schemas"]["ToolOut"];
type Database = components["schemas"]["DatabaseInfo"];
type Features = { [feature: string]: boolean }; // GET /v1/admin/tools/features (console_features.py kill switches)

// Where one of our servers reads its data (never the password) and whether its login answered when the page opened.
function DatabaseLine({ db }: { db: Database }) {
  if (!db.host) return <div className={`${styles.kpiNote} ${styles.error}`}>database {db.error}</div>;
  const where = `${db.host}${db.port ? `:${db.port}` : ""} / ${db.database ?? "?"} as ${db.user ?? "?"}`;
  return (
    <div className={`${styles.kpiNote} ${db.reachable ? "" : styles.error}`}>
      database <span className="mono">{where}</span> · {db.reachable ? "reachable" : `not reachable (${db.error})`}
    </div>
  );
}

// Why a listed tool is not offered right now (the first reason that applies).
function whyNotInUse(t: Tool, recordsSource: string | null): string {
  if (t.approval === "pending") return "waits for approval";
  if (t.approval === "changed") return "changed on the server: approve again";
  if (!t.enabled) return "switched off";
  if (t.kind !== "mcp" && recordsSource === "mcp") return "records source is the MCP server";
  return "records DB not set";
}

/** The brief description: the first sentence of what the model reads, up to its first colon (the details the model
 *  needs come after it), at most ~110 characters. */
function brief(description: string): string {
  let first = description.trim().split(/(?<=[.!?])\s/)[0] ?? "";
  const colon = first.indexOf(":");
  if (colon >= 20) first = first.slice(0, colon);
  return first.length > 110 ? `${first.slice(0, 109).trimEnd()}…` : first;
}

/** "hrdotnet__get_my_payslip" → its source ("hrdotnet") and its short name ("get_my_payslip"). */
function splitName(name: string): { source: string | null; short: string } {
  const at = name.indexOf("__");
  return at < 0 ? { source: null, short: name } : { source: name.slice(0, at), short: name.slice(at + 2) };
}

type Fields = { [key: string]: unknown } | null | undefined;

/** One value in the change log: words for on / off and empty, short text for the rest. */
function show(v: unknown): string {
  if (v === null || v === undefined || v === "") return "–";
  if (v === true) return "on";
  if (v === false) return "off";
  const text = typeof v === "string" ? v : JSON.stringify(v);
  return text.length > 80 ? `${text.slice(0, 79)}…` : text;
}

/** What a change did, one line per field that changed ("enabled: off → on"), instead of two JSON blobs. */
function changeLines(before: Fields, after: Fields): string[] {
  if (!before && !after) return ["–"];
  if (!before) return Object.entries(after!).map(([k, v]) => `${k}: ${show(v)}`); // added
  if (!after) return ["removed"];
  const keys = [...new Set([...Object.keys(before), ...Object.keys(after)])];
  const changed = keys.filter((k) => JSON.stringify(before[k]) !== JSON.stringify(after[k]));
  return changed.length ? changed.map((k) => `${k}: ${show(before[k])} → ${show(after[k])}`) : ["no change"];
}

/** "13 tools · 10 in use · 1 to approve" */
function countLine(tools: Tool[]): string {
  const inUse = tools.filter((t) => t.in_use).length;
  const waiting = tools.filter((t) => t.approval === "pending" || t.approval === "changed").length;
  return [
    `${tools.length} ${tools.length === 1 ? "tool" : "tools"}`,
    `${inUse} in use`,
    waiting ? `${waiting} to approve` : null,
  ]
    .filter(Boolean)
    .join(" · ");
}

type RowContext = { on: Features; locked: boolean; recordsSource: string | null };

/** One tool on one line: short name + brief description, where it is used, its state, its switch and buttons. */
function ToolRow({ t, ctx }: { t: Tool; ctx: RowContext }) {
  const { short } = splitName(t.name);
  return (
    <li className={`${css.toolRow} ${t.enabled ? "" : styles.dimmed}`}>
      <div className={css.toolMain}>
        <span className={`mono ${css.toolName}`} translate="no" title={t.name}>
          {short}
        </span>
        <span className={css.brief}>
          {brief(t.description)}
          {t.description_changed && <em> (edited)</em>}
        </span>
        <span className={styles.kpiNote}>
          {t.used_by.length ? (
            <>
              apps: <span className="mono">{t.used_by.join(", ")}</span>
            </>
          ) : (
            "no app has it yet"
          )}
        </span>
      </div>
      <div className={css.toolState}>
        {t.in_use ? (
          <span className={`${styles.withIcon} ${styles.ok}`}>
            <StatusOkIcon /> In use
          </span>
        ) : (
          <span className={styles.muted}>○ {whyNotInUse(t, ctx.recordsSource)}</span>
        )}
      </div>
      <div className={css.toolActions}>
        {ctx.on.tool_switches && <ToolSwitch name={t.name} enabled={t.enabled} />}
        {(t.approval === "pending" || t.approval === "changed") && (
          <ConfirmAction
            quiet
            locked={ctx.locked}
            label={t.approval === "pending" ? "Approve" : "Approve again"}
            title={`Approve ${t.name}?`}
            confirmLabel="Approve"
            action={approveTool.bind(null, t.name)}
            done={`${t.name} approved`}
          >
            <p>
              {t.approval === "pending"
                ? "This tool comes from a server on another machine. Once approved, the model is offered it."
                : "The server changed this tool's text or arguments since you approved it. Read it again."}
            </p>
            <p>
              <strong>What the model will read:</strong> {t.code_description}
            </p>
          </ConfirmAction>
        )}
        {ctx.on.edit_descriptions && (
          <DescriptionDialog
            name={t.name}
            description={t.description}
            codeDescription={t.code_description}
            changed={t.description_changed}
            locked={ctx.locked}
          />
        )}
        {ctx.on.code_view && <CodeButton name={t.name} locked={ctx.locked} />}
      </div>
    </li>
  );
}

/** A source's tools, folded: "Tools (13) · 10 in use". Open by itself when one waits for approval. */
function ToolFold({ tools, ctx, empty }: { tools: Tool[]; ctx: RowContext; empty: string }) {
  if (tools.length === 0) return <p className={styles.kpiNote}>{empty}</p>;
  const waiting = tools.some((t) => t.approval === "pending" || t.approval === "changed");
  return (
    <details className={css.fold} open={waiting}>
      <summary>
        Tools <span className={styles.muted}>({countLine(tools)})</span>
      </summary>
      <ul className={css.toolList}>
        {tools.map((t) => (
          <ToolRow key={t.name} t={t} ctx={ctx} />
        ))}
      </ul>
    </details>
  );
}

export default async function ToolsPage() {
  await testersGoToChat(); // testers have only the Chat page
  const me = await currentAccount();
  endSessionOn401(me);
  if (!me.ok || me.data.role !== "super_admin") {
    return (
      <Placeholder title="Tools & MCP" step="Super admin only">
        Only a super admin can see and change the tools and MCP connections. (FastAPI refuses these requests for
        anyone else.)
      </Placeholder>
    );
  }

  const features = await callApi((api) => api.GET("/v1/admin/tools/features"));
  endSessionOn401(features);
  if (!features.ok) return <Problem message={displayMessage(features.error)} />;
  const on = features.data;

  const [gate, settings, connections, stdioServers, status, tools, sqlTools, changes, tryScopes] = await Promise.all([
    callApi((api) => api.GET("/v1/admin/tools/gate")),
    on.records_source ? callApi((api) => api.GET("/v1/admin/tools/settings")) : null,
    on.mcp_connections ? callApi((api) => api.GET("/v1/admin/tools/connections")) : null,
    on.mcp_connections ? callApi((api) => api.GET("/v1/admin/tools/stdio-servers")) : null,
    on.server_status ? callApi((api) => api.GET("/v1/admin/tools/status")) : null,
    callApi((api) => api.GET("/v1/admin/tools/tools")),
    on.sql_tools ? callApi((api) => api.GET("/v1/admin/tools/sql-tools")) : null,
    callApi((api) => api.GET("/v1/admin/tools/changes", { params: { query: { limit: 30 } } })),
    on.try_it ? callApi((api) => api.GET("/v1/admin/tools/try/scopes")) : null,
  ]);
  for (const r of [gate, settings, connections, stdioServers, status, tools, sqlTools, changes, tryScopes]) if (r) endSessionOn401(r);
  const locked = !(gate.ok && gate.data.unlocked_until); // FastAPI decides; this only greys out the buttons
  const checks = new Map((status?.ok ? status.data : []).map((x) => [x.name, x])); // each connection's server check
  const ctx: RowContext = { on, locked, recordsSource: settings?.ok ? settings.data.records_source : null };

  // Sort the tools into their sources: built-in tools by system (the records tools have no prefix), each MCP
  // connection's tools by its name prefix, SQL tools. An MCP tool whose connection is gone lands in "other".
  const all = tools.ok ? tools.data : [];
  const connectionNames = new Set((connections?.ok ? connections.data : []).map((c) => c.name));
  const builtIn = new Map<string, Tool[]>();
  const byConnection = new Map<string, Tool[]>();
  const sqlKind: Tool[] = [];
  const other: Tool[] = [];
  for (const t of all) {
    const { source } = splitName(t.name);
    if (t.kind === "sql") sqlKind.push(t);
    else if (t.kind === "mcp") {
      if (source && connectionNames.has(source)) byConnection.set(source, [...(byConnection.get(source) ?? []), t]);
      else other.push(t);
    } else builtIn.set(source ?? "records", [...(builtIn.get(source ?? "records") ?? []), t]);
  }

  return (
    <>
      {gate.ok ? <GateBar gate={gate.data} /> : <Problem message={displayMessage(gate.error)} />}

      {settings && (
        <section className={`${styles.card} ${css.recordsCard}`} aria-labelledby="records-source">
          <div className={css.recordsText}>
            <h2 id="records-source">Who answers records questions</h2>
            <p className={styles.kpiNote}>
              Built-in: the AI host reads the records DB itself (fastest). Records MCP server: the same tools through
              MCP (1–2 s more). Applies to the next question.
            </p>
          </div>
          {!settings.ok ? (
            <Problem message={displayMessage(settings.error)} />
          ) : (
            <RecordsSourceSwitch current={settings.data.records_source} dbConfigured={settings.data.records_db_configured ?? false} />
          )}
        </section>
      )}

      <section aria-labelledby="sources" className={css.sources}>
        <div className={css.sourcesHead}>
          <h2 id="sources">Where the tools come from</h2>
          {stdioServers?.ok && <ConnectionDialog stdioServers={stdioServers.data} locked={locked} />}
        </div>
        {!tools.ok && <Problem message={displayMessage(tools.error)} />}
        {status && !status.ok && <Problem message={displayMessage(status.error)} />}

        {/* Built-in tools, one card per system (tools.py / systems/*.py) */}
        {[...builtIn.entries()].map(([system, list]) => (
          <article key={system} className={`${styles.card} ${css.source}`}>
            <div className={css.sourceHead}>
              <div className={css.sourceName}>
                <strong>
                  Built-in · <span className="mono">{system}</span>
                </strong>
                <span className={styles.kpiNote}>{system === "records" ? "tools.py" : `systems/${system}.py`}: runs inside the AI host</span>
              </div>
            </div>
            <ToolFold tools={list} ctx={ctx} empty="No tools." />
          </article>
        ))}

        {/* One card per MCP connection: how it is reached, its state, its buttons, its tools folded under it */}
        {connections && !connections.ok && <Problem message={displayMessage(connections.error)} />}
        {(connections?.ok ? connections.data : []).map((c) => {
          const check = checks.get(c.name);
          return (
            <article key={c.name} className={`${styles.card} ${css.source} ${c.enabled ? "" : styles.dimmed}`}>
              <div className={css.sourceHead}>
                <div className={css.sourceName}>
                  <strong>
                    MCP · <span className="mono">{c.name}</span>
                    {c.records && <span className={styles.tag}>records</span>}
                  </strong>
                  <span className={`${styles.kpiNote} mono ${styles.wrapAnywhere}`} translate="no">
                    {c.transport === "stdio" ? `stdio: ${c.server}` : c.url} · scope {c.scope}
                    {c.topics.length > 0 && ` · ${c.topics.join(", ")}`}
                  </span>
                </div>
                <div className={css.sourceState}>
                  {c.usable ? (
                    <span className={`${styles.withIcon} ${styles.ok}`}>
                      <StatusOkIcon /> In use
                    </span>
                  ) : (
                    <span className={styles.muted}>
                      ○ Not in use{!c.enabled ? " (disabled)" : c.records ? " (records source is built-in)" : ""}
                    </span>
                  )}
                  {check ? (
                    <span className={`${styles.kpiNote} ${check.ok ? "" : styles.error}`}>
                      {check.ok ? `answers in ${check.seconds} s` : `not answering: ${check.error}`}
                    </span>
                  ) : (
                    on.server_status && <span className={styles.kpiNote}>not checked (disabled)</span>
                  )}
                  {c.transport !== "stdio" &&
                    (c.secret_set ? (
                      <span className={`${styles.withIcon} ${styles.kpiNote}`}>
                        <StatusOkIcon /> secret set {c.token_env && <span className="mono">({c.token_env})</span>}
                      </span>
                    ) : (
                      <span className={`${styles.withIcon} ${styles.warn}`}>
                        <StatusWarnIcon /> secret missing {c.token_env && <span className="mono">({c.token_env})</span>}
                      </span>
                    ))}
                  {check?.database && <DatabaseLine db={check.database} />}
                </div>
                <div className={styles.rowActions}>
                  {on.server_status && <TestButton name={c.name} />}
                  {stdioServers?.ok && <ConnectionDialog connection={c} stdioServers={stdioServers.data} locked={locked} />}
                  <ConfirmAction
                    locked={locked}
                    label="Delete"
                    title={`Delete the connection ${c.name}?`}
                    confirmLabel="Delete"
                    action={deleteConnection.bind(null, c.name)}
                    done={`Connection ${c.name} deleted`}
                  >
                    <p>
                      Its tools stop being offered at once. The server itself is not touched; you can add the
                      connection again later.
                    </p>
                  </ConfirmAction>
                </div>
              </div>
              <ToolFold
                tools={byConnection.get(c.name) ?? []}
                ctx={ctx}
                empty={
                  check?.tools.length
                    ? `Offers ${check.tools.join(", ")} (not listed: switched off in the console or no matching scope).`
                    : c.enabled
                      ? "No tools from this server right now."
                      : "Disabled: its tools are not offered."
                }
              />
            </article>
          );
        })}

        {other.length > 0 && (
          <article className={`${styles.card} ${css.source}`}>
            <div className={css.sourceHead}>
              <div className={css.sourceName}>
                <strong>Other MCP tools</strong>
                <span className={styles.kpiNote}>from a server that is no longer a connection here</span>
              </div>
            </div>
            <ToolFold tools={other} ctx={ctx} empty="" />
          </article>
        )}

        {/* SQL tools: the definitions (SQL, arguments) and, folded, the tools as the model sees them */}
        {sqlTools && (
          <article className={`${styles.card} ${css.source}`}>
            <div className={css.sourceHead}>
              <div className={css.sourceName}>
                <strong>SQL tools</strong>
                <span className={styles.kpiNote}>read-only queries on the records DB, written here</span>
              </div>
              <div className={styles.rowActions}>
                <SqlToolDialog locked={locked} />
              </div>
            </div>
            {!sqlTools.ok ? (
              <Problem message={displayMessage(sqlTools.error)} />
            ) : sqlTools.data.length === 0 ? (
              <p className={styles.kpiNote}>No SQL tools yet.</p>
            ) : (
              <details className={css.fold}>
                <summary>
                  Tools <span className={styles.muted}>({countLine(sqlKind)})</span>
                </summary>
                <ul className={css.toolList}>
                  {sqlTools.data.map((s) => {
                    const t = sqlKind.find((x) => x.name === s.name);
                    return (
                      <li key={s.name} className={`${css.toolRow} ${s.enabled ? "" : styles.dimmed}`}>
                        <div className={css.toolMain}>
                          <span className={`mono ${css.toolName}`} translate="no">
                            {s.name}
                          </span>
                          <span className={css.brief}>{t ? brief(t.description) : ""}</span>
                          <span className={`${styles.kpiNote} mono ${styles.wrapAnywhere}`}>
                            {s.sql}
                            {(s.parameters ?? []).length > 0 &&
                              ` · ${(s.parameters ?? []).map((p) => `${p.name}: ${p.type}`).join(", ")}`}
                          </span>
                        </div>
                        <div className={css.toolState}>
                          {s.enabled ? (
                            <span className={`${styles.withIcon} ${styles.ok}`}>
                              <StatusOkIcon /> On
                            </span>
                          ) : (
                            <span className={styles.muted}>○ Off</span>
                          )}
                        </div>
                        <div className={css.toolActions}>
                          <SqlToolDialog tool={s} locked={locked} />
                          <ConfirmAction
                            locked={locked}
                            label="Delete"
                            title={`Delete the SQL tool ${s.name}?`}
                            confirmLabel="Delete"
                            action={deleteSqlTool.bind(null, s.name)}
                            done={`SQL tool ${s.name} deleted`}
                          >
                            <p>The model stops being offered it at once. The change log keeps its SQL.</p>
                          </ConfirmAction>
                          {t && ctx.on.code_view && <CodeButton name={t.name} locked={locked} />}
                        </div>
                      </li>
                    );
                  })}
                </ul>
              </details>
            )}
          </article>
        )}

        {tools.ok && all.length === 0 && (
          <p className={styles.muted}>No tools right now (records DB not set, or no usable MCP connection).</p>
        )}
      </section>

      {tryScopes && (
        <details className={`${styles.card} ${css.foldCard}`}>
          <summary>
            <h2 id="try-it">Try it: ask as a test employee</h2>
            <span className={styles.kpiNote}>the real tool loop, with only the scopes you tick</span>
          </summary>
          {!tryScopes.ok ? <Problem message={displayMessage(tryScopes.error)} /> : <TryItPanel scopes={tryScopes.data} locked={locked} />}
        </details>
      )}

      <details className={`${styles.card} ${css.foldCard}`}>
        <summary>
          <h2 id="changes">Change log</h2>
          <span className={styles.kpiNote}>
            {changes.ok ? `last ${changes.data.length} changes${changes.data[0] ? `, latest ${formatDateTime(changes.data[0].at)}` : ""}` : ""}
          </span>
        </summary>
        {!changes.ok ? (
          <Problem message={displayMessage(changes.error)} />
        ) : changes.data.length === 0 ? (
          <p className={styles.muted}>Nothing changed here yet.</p>
        ) : (
          <ul className={css.changeList}>
            {changes.data.map((c, i) => (
              <li key={`${c.at}-${i}`}>
                <span className={styles.kpiNote}>{formatDateTime(c.at)}</span>
                <span>
                  <span className="mono">{c.who}</span> · {c.what} · <span className="mono">{c.target}</span>
                </span>
                <span className={`mono ${styles.wrapAnywhere} ${css.changeLines}`}>
                  {changeLines(c.old, c.new).join(" · ")}
                </span>
              </li>
            ))}
          </ul>
        )}
      </details>
      {status?.ok && <p className={styles.kpiNote}>Servers checked when this page opened.</p>}
    </>
  );
}

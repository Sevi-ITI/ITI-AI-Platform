// Copied from admin-ui src/app/(console)/tools/page.tsx (G6). Same FastAPI calls and data; the panel header shows the room title.
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

export const metadata = { title: "Tools & MCP" };

type Tool = components["schemas"]["ToolOut"];
type Database = components["schemas"]["DatabaseInfo"];

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

// Tools & MCP (super admin only, Phase 8.6d): who answers records questions, the MCP connections, which tools the
// model is offered, and every change made here. Each section exists only while its kill switch in
// backend/app/tools/console_features.py is True; FastAPI refuses a switched-off part too. Secrets are never shown:
// a connection names its backend\.env variable and the page says whether it is set.
// 8.6e-3: the risky changes (connections, approvals, descriptions, SQL tools, Try it, the code view) need the security
// password unlocked (the gate bar under the title); while locked they are greyed out with a padlock.
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
  // each connection's server check, by name (shown in its row)
  const checks = new Map((status?.ok ? status.data : []).map((x) => [x.name, x]));

  return (
    <>
      {gate.ok ? <GateBar gate={gate.data} /> : <Problem message={displayMessage(gate.error)} />}
      {/* a long page: jump links to its parts (only the parts switched on in console_features.py) */}
      <nav className={styles.jumpLinks} aria-label="On this page">
        {[
          settings && { id: "records-source", label: "Records source" },
          connections && { id: "connections", label: "Connections" },
          { id: "tools", label: "Tools" },
          tryScopes && { id: "try-it", label: "Try it" },
          sqlTools && { id: "sql-tools", label: "SQL tools" },
          { id: "changes", label: "Changes" },
        ]
          .filter((x): x is { id: string; label: string } => Boolean(x))
          .map((x) => (
            <a key={x.id} href={`#${x.id}`} className={styles.smallButton}>
              {x.label}
            </a>
          ))}
      </nav>

      {settings && (
        <section className={styles.card} aria-labelledby="records-source">
          <div className={styles.cardHead}>
            <h2 id="records-source">Who answers records questions</h2>
          </div>
          {!settings.ok ? (
            <Problem message={displayMessage(settings.error)} />
          ) : (
            <>
              <p className={styles.muted}>
                Built-in tools: the AI host reads the records DB itself (fastest). Records MCP server: the same tools
                through the MCP server (about 1–2 s more per question). The change applies to the next question.
              </p>
              <RecordsSourceSwitch
                current={settings.data.records_source}
                dbConfigured={settings.data.records_db_configured ?? false}
              />
            </>
          )}
        </section>
      )}

      {connections && (
        <section className={styles.card} aria-labelledby="connections">
          <div className={styles.cardHead}>
            <h2 id="connections">MCP connections</h2>
            {stdioServers?.ok && <ConnectionDialog stdioServers={stdioServers.data} locked={locked} />}
          </div>
          {/* the server check (was its own card) is now each connection's second line under State */}
          {status && !status.ok && <Problem message={displayMessage(status.error)} />}
          {!connections.ok ? (
            <Problem message={displayMessage(connections.error)} />
          ) : connections.data.length === 0 ? (
            <p className={styles.muted}>No connections yet.</p>
          ) : (
            <div className={styles.tableWrap}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th scope="col">Connection</th>
                    <th scope="col">Scope</th>
                    <th scope="col">Topics</th>
                    <th scope="col">Secret</th>
                    <th scope="col">State</th>
                    <th scope="col" className={styles.actionsCell}>{/* actions */}</th>
                  </tr>
                </thead>
                <tbody>
                  {connections.data.map((c) => {
                    const check = checks.get(c.name);
                    return (
                      <tr key={c.name} className={c.enabled ? undefined : styles.dimmed}>
                        {/* name (+ records), how it is reached, and the tools it offered at the check */}
                        <td className={styles.toolCell}>
                          <span className={`mono ${styles.nowrap}`} translate="no">
                            {c.name}
                          </span>
                          {c.records && <span className={styles.tag}>records</span>}
                          <div className={`${styles.kpiNote} mono`} translate="no">
                            {c.transport === "stdio" ? `stdio: ${c.server}` : c.url}
                          </div>
                          {check && check.tools.length > 0 && (
                            <div className={`${styles.kpiNote} mono ${styles.wrapAnywhere}`} translate="no">
                              offers {check.tools.join(", ")}
                            </div>
                          )}
                        </td>
                        <td className="mono">{c.scope}</td>
                        <td>{c.topics.join(", ")}</td>
                        <td className={styles.nowrap}>
                          {c.transport === "stdio" ? (
                            <span className={styles.muted}>not needed</span>
                          ) : c.secret_set ? (
                            <span className={`${styles.withIcon} ${styles.ok}`}>
                              <StatusOkIcon /> set
                            </span>
                          ) : (
                            <span className={`${styles.withIcon} ${styles.warn}`}>
                              <StatusWarnIcon /> missing
                            </span>
                          )}
                          {c.token_env && <div className={`${styles.kpiNote} mono`}>{c.token_env}</div>}
                        </td>
                        <td className={styles.reasonCell}>
                          {c.usable ? (
                            <span className={`${styles.withIcon} ${styles.ok}`}>
                              <StatusOkIcon /> In use
                            </span>
                          ) : (
                            <span className={styles.muted}>
                              ○ Not in use
                              {!c.enabled ? " (disabled)" : c.records ? " (records source is built-in)" : ""}
                            </span>
                          )}
                          {/* the check when this page opened (enabled connections only) */}
                          {check ? (
                            <div className={`${styles.kpiNote} ${check.ok ? "" : styles.error}`}>
                              {check.ok ? `answers in ${check.seconds} s` : `not answering: ${check.error}`}
                            </div>
                          ) : (
                            on.server_status && <div className={styles.kpiNote}>not checked (disabled)</div>
                          )}
                          {check?.database && <DatabaseLine db={check.database} />}
                        </td>
                        <td className={styles.actionsCell}>
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
                                Its tools stop being offered at once. The server itself is not touched; you can add
                                the connection again later.
                              </p>
                            </ConfirmAction>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
          {status?.ok && <p className={styles.kpiNote}>Servers checked when this page opened.</p>}
        </section>
      )}

      <section className={styles.card} aria-labelledby="tools">
        <div className={styles.cardHead}>
          <h2 id="tools">Tools the model can be offered</h2>
        </div>
        {!tools.ok ? (
          <Problem message={displayMessage(tools.error)} />
        ) : tools.data.length === 0 ? (
          <p className={styles.muted}>No tools right now (records DB not set, or no usable MCP connection).</p>
        ) : (
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th scope="col">Tool and what the model reads</th>
                  <th scope="col">From</th>
                  <th scope="col">Scope</th>
                  <th scope="col" className={styles.nowrap}>
                    Used by
                  </th>
                  <th scope="col" className={styles.nowrap}>
                    In use
                  </th>
                  {on.tool_switches && <th scope="col">On</th>}
                  <th scope="col" className={styles.actionsCell}>{/* actions */}</th>
                </tr>
              </thead>
              <tbody>
                {tools.data.map((t) => (
                  <tr key={t.name} className={t.enabled ? undefined : styles.dimmed}>
                    {/* The description sits under the name at full width: its own column got squeezed to a few
                        words per line beside the nowrap columns. */}
                    <td className={styles.toolCell}>
                      <span className={`mono ${styles.nowrap}`} translate="no">
                        {t.name}
                      </span>
                      <p className={styles.muted}>
                        {t.description}
                        {t.description_changed && <em> (changed in the console)</em>}
                      </p>
                    </td>
                    <td className={styles.nowrap}>{t.kind === "built-in" ? "tools.py" : t.kind === "sql" ? "SQL tool" : "MCP server"}</td>
                    <td className="mono">{t.scope}</td>
                    {/* 8.6e-2: the apps whose tool list has it (ticked on Apps & keys) */}
                    <td className="mono">
                      {t.used_by.length ? t.used_by.join(", ") : <span className={styles.muted}>no app</span>}
                    </td>
                    <td className={styles.reasonCell}>
                      {t.in_use ? (
                        <span className={`${styles.withIcon} ${styles.ok}`}>
                          <StatusOkIcon /> Yes
                        </span>
                      ) : (
                        <span className={styles.muted}>○ No ({whyNotInUse(t, settings?.ok ? settings.data.records_source : null)})</span>
                      )}
                    </td>
                    {on.tool_switches && (
                      <td>
                        <ToolSwitch name={t.name} enabled={t.enabled} />
                      </td>
                    )}
                    <td className={styles.actionsCell}>
                      <div className={styles.rowActions}>
                        {(t.approval === "pending" || t.approval === "changed") && (
                          <ConfirmAction
                            quiet
                            locked={locked}
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
                        {on.edit_descriptions && (
                          <DescriptionDialog
                            name={t.name}
                            description={t.description}
                            codeDescription={t.code_description}
                            changed={t.description_changed}
                            locked={locked}
                          />
                        )}
                        {on.code_view && <CodeButton name={t.name} locked={locked} />}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {tryScopes && (
        <section className={styles.card} aria-labelledby="try-it">
          <div className={styles.cardHead}>
            <h2 id="try-it">Try it: ask as a test employee</h2>
          </div>
          <p className={styles.muted}>
            Runs the same tool loop as the real chat, with only the scopes you tick, and shows which tools the model
            called with which arguments.
          </p>
          {!tryScopes.ok ? <Problem message={displayMessage(tryScopes.error)} /> : <TryItPanel scopes={tryScopes.data} locked={locked} />}
        </section>
      )}

      {sqlTools && (
        <section className={styles.card} aria-labelledby="sql-tools">
          <div className={styles.cardHead}>
            <h2 id="sql-tools">SQL tools</h2>
            <SqlToolDialog locked={locked} />
          </div>
          {!sqlTools.ok ? (
            <Problem message={displayMessage(sqlTools.error)} />
          ) : sqlTools.data.length === 0 ? (
            <p className={styles.muted}>No SQL tools yet.</p>
          ) : (
            <div className={styles.tableWrap}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th scope="col">Name</th>
                    <th scope="col">SQL</th>
                    <th scope="col">Arguments</th>
                    <th scope="col">State</th>
                    <th scope="col" className={styles.actionsCell}>{/* actions */}</th>
                  </tr>
                </thead>
                <tbody>
                  {sqlTools.data.map((t) => (
                    <tr key={t.name} className={t.enabled ? undefined : styles.dimmed}>
                      <td className={`mono ${styles.nowrap}`} translate="no">
                        {t.name}
                      </td>
                      <td className={`mono ${styles.wrapAnywhere}`}>{t.sql}</td>
                      <td className="mono">{(t.parameters ?? []).map((p) => `${p.name}: ${p.type}`).join(", ") || "–"}</td>
                      <td className={styles.nowrap}>
                        {t.enabled ? (
                          <span className={`${styles.withIcon} ${styles.ok}`}>
                            <StatusOkIcon /> On
                          </span>
                        ) : (
                          <span className={styles.muted}>○ Off</span>
                        )}
                      </td>
                      <td className={styles.actionsCell}>
                        <div className={styles.rowActions}>
                          <SqlToolDialog tool={t} locked={locked} />
                          <ConfirmAction
                            locked={locked}
                            label="Delete"
                            title={`Delete the SQL tool ${t.name}?`}
                            confirmLabel="Delete"
                            action={deleteSqlTool.bind(null, t.name)}
                            done={`SQL tool ${t.name} deleted`}
                          >
                            <p>The model stops being offered it at once. The change log keeps its SQL.</p>
                          </ConfirmAction>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}

      <section className={styles.card} aria-labelledby="changes">
        <div className={styles.cardHead}>
          <h2 id="changes">Changes (last 30)</h2>
        </div>
        {!changes.ok ? (
          <Problem message={displayMessage(changes.error)} />
        ) : changes.data.length === 0 ? (
          <p className={styles.muted}>Nothing changed here yet.</p>
        ) : (
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th scope="col">When</th>
                  <th scope="col">Who</th>
                  <th scope="col">What</th>
                  <th scope="col">On</th>
                  <th scope="col">Change</th>
                </tr>
              </thead>
              <tbody>
                {changes.data.map((c, i) => (
                  <tr key={`${c.at}-${i}`}>
                    <td className={styles.nowrap}>{formatDateTime(c.at)}</td>
                    <td className={`mono ${styles.nowrap}`}>{c.who}</td>
                    <td className={`mono ${styles.nowrap}`}>{c.what}</td>
                    <td className={`mono ${styles.nowrap}`}>{c.target}</td>
                    <td className={styles.wrapAnywhere}>
                      {changeLines(c.old, c.new).map((line, j) => (
                        <div key={j} className="mono">
                          {line}
                        </div>
                      ))}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </>
  );
}

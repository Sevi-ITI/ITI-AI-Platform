import { displayMessage } from "@/lib/api/api-error";
import { callApi, endSessionOn401 } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";
import { formatDateTime } from "@/lib/format";
import { currentAccount } from "@/lib/session/current-account";

import ConfirmAction from "../confirm-action";
import styles from "../dashboard.module.css";
import Placeholder from "../placeholder";
import { Problem } from "../widgets";
import { approveTool, deleteConnection, deleteSqlTool } from "./actions";
import {
  ConnectionDialog,
  DescriptionDialog,
  RecordsSourceSwitch,
  SqlToolDialog,
  TestButton,
  ToolSwitch,
} from "./controls";

export const metadata = { title: "Tools & MCP" };

type Tool = components["schemas"]["ToolOut"];

// Why a listed tool is not offered right now (the first reason that applies).
function whyNotInUse(t: Tool, recordsSource: string | null): string {
  if (t.approval === "pending") return "waits for approval";
  if (t.approval === "changed") return "changed on the server: approve again";
  if (!t.enabled) return "switched off";
  if (t.kind !== "mcp" && recordsSource === "mcp") return "records source is the MCP server";
  return "records DB not set";
}

// Tools & MCP (super admin only, Phase 8.6d): who answers records questions, the MCP connections, which tools the
// model is offered, and every change made here. Each section exists only while its kill switch in
// backend/app/tools/console_features.py is True; FastAPI refuses a switched-off part too. Secrets are never shown:
// a connection names its backend\.env variable and the page says whether it is set.
export default async function ToolsPage() {
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

  const [settings, connections, stdioServers, status, tools, sqlTools, changes] = await Promise.all([
    on.records_source ? callApi((api) => api.GET("/v1/admin/tools/settings")) : null,
    on.mcp_connections ? callApi((api) => api.GET("/v1/admin/tools/connections")) : null,
    on.mcp_connections ? callApi((api) => api.GET("/v1/admin/tools/stdio-servers")) : null,
    on.server_status ? callApi((api) => api.GET("/v1/admin/tools/status")) : null,
    callApi((api) => api.GET("/v1/admin/tools/tools")),
    on.sql_tools ? callApi((api) => api.GET("/v1/admin/tools/sql-tools")) : null,
    callApi((api) => api.GET("/v1/admin/tools/changes", { params: { query: { limit: 30 } } })),
  ]);
  for (const r of [settings, connections, stdioServers, status, tools, sqlTools, changes]) if (r) endSessionOn401(r);

  return (
    <>
      <header className={styles.header}>
        <h1>Tools &amp; MCP</h1>
      </header>

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
            {stdioServers?.ok && <ConnectionDialog stdioServers={stdioServers.data} />}
          </div>
          {!connections.ok ? (
            <Problem message={displayMessage(connections.error)} />
          ) : connections.data.length === 0 ? (
            <p className={styles.muted}>No connections yet.</p>
          ) : (
            <div className={styles.tableWrap}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th scope="col">Name</th>
                    <th scope="col">Reached by</th>
                    <th scope="col">Scope</th>
                    <th scope="col">Topics</th>
                    <th scope="col">Secret set</th>
                    <th scope="col">In use</th>
                    <th scope="col" className={styles.actionsCell}>{/* actions */}</th>
                  </tr>
                </thead>
                <tbody>
                  {connections.data.map((c) => (
                    <tr key={c.name} className={c.enabled ? undefined : styles.dimmed}>
                      <td className={`mono ${styles.nowrap}`} translate="no">
                        {c.name}
                        {c.records && <span className={styles.muted}> (records)</span>}
                      </td>
                      <td className="mono" translate="no">
                        {c.transport === "stdio" ? `stdio: ${c.server}` : c.url}
                      </td>
                      <td className="mono">{c.scope}</td>
                      <td>{c.topics.join(", ")}</td>
                      <td className={styles.nowrap}>
                        {c.transport === "stdio" ? (
                          <span className={styles.muted}>not needed</span>
                        ) : c.secret_set ? (
                          <span className={styles.ok}>● yes ({c.token_env})</span>
                        ) : (
                          <span className={styles.warn}>○ no: set {c.token_env} in backend\.env</span>
                        )}
                      </td>
                      <td className={styles.nowrap}>
                        {c.usable ? (
                          <span className={styles.ok}>● Yes</span>
                        ) : (
                          <span className={styles.muted}>
                            ○ No{!c.enabled ? " (disabled)" : c.records ? " (records source is built-in)" : ""}
                          </span>
                        )}
                      </td>
                      <td className={styles.actionsCell}>
                        <div className={styles.rowActions}>
                          {on.server_status && <TestButton name={c.name} />}
                          {stdioServers?.ok && <ConnectionDialog connection={c} stdioServers={stdioServers.data} />}
                          <ConfirmAction
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
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}

      {status && (
        <section className={styles.card} aria-labelledby="status">
          <div className={styles.cardHead}>
            <h2 id="status">Server status (checked when this page opened)</h2>
          </div>
          {!status.ok ? (
            <Problem message={displayMessage(status.error)} />
          ) : status.data.length === 0 ? (
            <p className={styles.muted}>No enabled connections to check.</p>
          ) : (
            <div className={styles.tableWrap}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th scope="col">Connection</th>
                    <th scope="col">Answers</th>
                    <th scope="col">Tools</th>
                    <th scope="col">Time</th>
                  </tr>
                </thead>
                <tbody>
                  {status.data.map((s) => (
                    <tr key={s.name}>
                      <td className={`mono ${styles.nowrap}`}>{s.name}</td>
                      <td className={styles.nowrap}>
                        {s.ok ? <span className={styles.ok}>● Yes</span> : <span className={styles.warn}>✕ No: {s.error}</span>}
                      </td>
                      <td className="mono">{s.tools.join(", ") || "–"}</td>
                      <td className={styles.nowrap}>{s.seconds} s</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
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
                    <td className={styles.reasonCell}>
                      {t.in_use ? (
                        <span className={styles.ok}>● Yes</span>
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
                          />
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {sqlTools && (
        <section className={styles.card} aria-labelledby="sql-tools">
          <div className={styles.cardHead}>
            <h2 id="sql-tools">SQL tools</h2>
            <SqlToolDialog />
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
                        {t.enabled ? <span className={styles.ok}>● On</span> : <span className={styles.muted}>○ Off</span>}
                      </td>
                      <td className={styles.actionsCell}>
                        <div className={styles.rowActions}>
                          <SqlToolDialog tool={t} />
                          <ConfirmAction
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
                    <td className={`mono ${styles.wrapAnywhere}`}>
                      {c.old ? JSON.stringify(c.old) : "–"} → {c.new ? JSON.stringify(c.new) : "–"}
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

// Documents, redesigned for game-ui (Vince, 2026-10-27: "too unorganized"). Not a copy of admin-ui's page any more:
// the same FastAPI calls (check:parity) and the same dialogs and actions (actions.ts, move / share: copies,
// check:rooms), a library layout instead of two long tables: the collections on the left (by owner company), the
// chosen collection on the right (who it belongs to, its buttons, its files). It opens on the first collection, not
// on every file; "All files" is still one click away. Failed uploads come first, older replaced versions fold away.
import Link from "next/link";

import { displayMessage } from "@/lib/api/api-error";
import { callApi, endSessionOn401 } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";
import { formatBytes, formatCount, formatDateTime } from "@/lib/format";
import { currentAccount } from "@/lib/session/current-account";
import { testersGoToChat } from "@/lib/session/testers-go-to-chat";

import AddDocument from "../chat/add-document";
import ConfirmAction from "../kit/confirm-action";
import styles from "../kit/dashboard.module.css";
import { StatusErrorIcon, StatusOkIcon } from "../kit/icons";
import Pager from "../kit/pager";
import { Problem } from "../kit/widgets";
import { deleteCollection, deleteDocument } from "./actions";
import css from "./documents.module.css";
import MoveCollectionButton from "./move-collection";
import ShareCollectionButton from "./share-collection";

export const metadata = { title: "Documents" };

const PAGE_SIZE = 100;

type Row = components["schemas"]["DocumentRow"];
type Collection = components["schemas"]["CollectionInfo"];
type Company = { company_id: string; name: string };

export default async function DocumentsPage({ searchParams }: PageProps<"/documents">) {
  await testersGoToChat(); // testers have only the Chat page
  const params = await searchParams;
  const one = (v: string | string[] | undefined) => (typeof v === "string" ? v.trim() : "");
  const page = Math.max(1, Number.parseInt(one(params.page), 10) || 1);
  const showAll = one(params.all) === "1";

  const [collections, companies, me] = await Promise.all([
    callApi((api) => api.GET("/v1/admin/collections")),
    callApi((api) => api.GET("/v1/admin/companies")),
    currentAccount(),
  ]);
  endSessionOn401(collections, companies, me);
  const companyList: Company[] = companies.ok ? companies.data.map((c) => ({ company_id: c.company_id, name: c.name })) : [];
  const isSuperAdmin = me.ok && me.data.role === "super_admin";

  // The collections by owner: each company (A to Z), then Global
  const owners = [...companyList, { company_id: null as string | null, name: "Global" }];
  const grouped = owners
    .map((o) => ({ owner: o, list: (collections.ok ? collections.data : []).filter((c) => (c.company_id ?? null) === o.company_id) }))
    .filter((g) => g.list.length > 0);
  // The open collection: the one in the URL, else the first one (not every file at once)
  const asked = one(params.collection);
  const selected = showAll ? null : (collections.ok ? collections.data : []).find((c) => c.name === asked) ?? grouped[0]?.list[0] ?? null;

  const rows = await callApi((api) =>
    api.GET("/v1/admin/documents", {
      params: { query: { collection: selected?.name, limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE } },
    }),
  );
  endSessionOn401(rows);

  const pageHref = (p: number) => {
    const q = new URLSearchParams();
    if (showAll) q.set("all", "1");
    else if (selected) q.set("collection", selected.name);
    if (p > 1) q.set("page", String(p));
    return `/documents?${q.toString()}`;
  };
  const ownerName = (c: Collection) => companyList.find((x) => x.company_id === c.company_id)?.name ?? "Global";

  // Sort the uploads: failed ones first (they need a look), then the live files, older replaced versions last
  const marked = rows.ok ? markReplaced(rows.data) : [];
  const failed = marked.filter((m) => !m.replaced && m.row.job_status === "failed");
  const live = marked.filter((m) => !m.replaced && m.row.job_status !== "failed");
  const older = marked.filter((m) => m.replaced);

  return (
    <>
      <div className={css.top}>
        <p className={styles.muted}>
          {collections.ok
            ? `${collections.data.length} collections · ${formatCount(collections.data.reduce((n, c) => n + c.documents, 0))} files`
            : ""}
        </p>
        {collections.ok && (
          <AddDocument
            collections={collections.data.map((c) => c.name)}
            initial={selected?.name}
            label="Upload document"
            canReplace={isSuperAdmin}
            companies={companyList}
          />
        )}
      </div>
      {!collections.ok && <Problem message={displayMessage(collections.error)} />}

      <div className={css.library}>
        {/* The collections, by owner company */}
        <nav className={`${styles.card} ${css.shelf}`} aria-label="Collections">
          <Link href="/documents?all=1" className={css.shelfLink} aria-current={showAll ? "page" : undefined}>
            All files
          </Link>
          {grouped.map(({ owner, list }) => (
            <div key={owner.company_id ?? "global"} className={css.shelfGroup}>
              <p className={css.shelfOwner}>{owner.name}</p>
              {list.map((c) => (
                <Link
                  key={c.name}
                  href={`/documents?collection=${encodeURIComponent(c.name)}`}
                  className={css.shelfLink}
                  aria-current={selected?.name === c.name ? "page" : undefined}
                >
                  <span className="mono" translate="no">
                    {c.name}
                  </span>
                  <span className={css.count}>{formatCount(c.documents)}</span>
                </Link>
              ))}
            </div>
          ))}
        </nav>

        {/* The chosen collection (or every file) */}
        <section className={`${styles.card} ${css.shelfDetail}`} aria-labelledby="collection-title">
          {selected ? (
            <CollectionHead c={selected} owner={ownerName(selected)} companies={companyList} canEdit={isSuperAdmin} />
          ) : (
            <div className={css.detailHead}>
              <h2 id="collection-title">All files</h2>
              <p className={styles.kpiNote}>Every upload in every collection, newest first.</p>
            </div>
          )}

          {!rows.ok ? (
            <Problem message={displayMessage(rows.error)} />
          ) : marked.length === 0 ? (
            <p className={styles.muted}>
              {page > 1 ? "No more documents." : "No documents here yet. Upload one with the button above."}
            </p>
          ) : (
            <>
              {failed.length > 0 && (
                <div className={css.attention}>
                  <p className={`${styles.withIcon} ${styles.error}`}>
                    <StatusErrorIcon /> {failed.length} {failed.length === 1 ? "upload" : "uploads"} failed
                  </p>
                  <ul className={css.files}>
                    {failed.map(({ row }) => (
                      <FileRow key={row.document_id} row={row} replaced={false} canDelete={isSuperAdmin} showCollection={showAll} />
                    ))}
                  </ul>
                </div>
              )}
              <ul className={css.files}>
                {live.map(({ row }) => (
                  <FileRow key={row.document_id} row={row} replaced={false} canDelete={isSuperAdmin} showCollection={showAll} />
                ))}
              </ul>
              {older.length > 0 && (
                <details className={css.older}>
                  <summary>
                    Older versions <span className={styles.muted}>({older.length}, replaced by a newer upload)</span>
                  </summary>
                  <ul className={css.files}>
                    {older.map(({ row }) => (
                      <FileRow key={row.document_id} row={row} replaced canDelete={false} showCollection={showAll} />
                    ))}
                  </ul>
                </details>
              )}
              {(page > 1 || marked.length === PAGE_SIZE) && (
                <Pager page={page} count={marked.length} pageSize={PAGE_SIZE} noun="Files" href={pageHref} />
              )}
            </>
          )}
        </section>
      </div>
    </>
  );
}

// The table is an upload history (newest first). An older indexed version of a file is "replaced" once a newer
// version of the same name in the same collection is indexed: its passages were swapped out at that moment.
// (A newer upload that failed replaced nothing: the old version stays live.)
// ponytail: decided within this page of 100; a replaced version whose newer copy is on an earlier page shows as live.
function markReplaced(rows: Row[]): { row: Row; replaced: boolean }[] {
  const live = new Set<string>();
  return rows.map((row) => {
    const key = `${row.collection}/${row.filename}`;
    const replaced = row.job_status === "done" && live.has(key);
    if (row.job_status === "done") live.add(key);
    return { row, replaced };
  });
}

/** The chosen collection: name, counts, who it belongs to and who else may use it, and the super admin's buttons. */
function CollectionHead({ c, owner, companies, canEdit }: { c: Collection; owner: string; companies: Company[]; canEdit: boolean }) {
  const empty = c.documents === 0 && c.chunks === 0;
  const shared = c.shared_with.map((id) => companies.find((x) => x.company_id === id)?.name ?? id);
  return (
    <div className={css.detailHead}>
      <div className={css.detailTitle}>
        <h2 id="collection-title" className="mono" translate="no">
          {c.name}
        </h2>
        <p className={styles.kpiNote}>
          {formatCount(c.documents)} files · {formatCount(c.chunks)} passages · belongs to {owner}
          {c.company_id === null && " (any company's key may get it)"}
          {shared.length > 0 && ` · also shared with ${shared.join(", ")}`}
        </p>
      </div>
      {canEdit && (
        <div className={styles.rowActions}>
          <MoveCollectionButton name={c.name} current={c.company_id ?? null} companies={companies} />
          {c.company_id && <ShareCollectionButton name={c.name} owner={c.company_id} sharedWith={c.shared_with} companies={companies} />}
          {c.in_settings ? (
            <span className={styles.actionNote} title="Listed in ITI_COLLECTIONS: it would come back at the next restart">
              Kept: server settings
            </span>
          ) : !empty ? (
            <span className={styles.actionNote} title="Delete its files first">
              Kept: has files
            </span>
          ) : (
            <ConfirmAction
              label="Delete"
              title={`Delete the collection ${c.name}?`}
              confirmLabel="Delete collection"
              action={deleteCollection.bind(null, c.name)}
              done={`Collection ${c.name} deleted`}
            >
              <p>
                The empty collection <strong className="mono">{c.name}</strong> is removed and taken off every API key
                that lists it. Old chats in it stay readable in Users &amp; chats but can&apos;t be continued.
              </p>
            </ConfirmAction>
          )}
        </div>
      )}
    </div>
  );
}

/** One upload on one line: name, size · when · who, its state and passages, Delete (on its newest version). */
function FileRow({ row, replaced, canDelete, showCollection }: { row: Row; replaced: boolean; canDelete: boolean; showCollection: boolean }) {
  const status = replaced ? (
    <span className={styles.muted} title="A newer upload of this file replaced it; its passages are no longer searched">
      ○ Replaced
    </span>
  ) : row.job_status === "done" ? (
    <span className={`${styles.withIcon} ${styles.ok}`}>
      <StatusOkIcon /> Indexed{row.chunks != null && ` · ${formatCount(row.chunks)} passages`}
    </span>
  ) : row.job_status === "failed" ? (
    <span className={`${styles.withIcon} ${styles.error}`}>
      <StatusErrorIcon /> Failed
    </span>
  ) : (
    <span className={styles.warn}>◌ Indexing…</span>
  );
  return (
    <li className={`${css.file} ${replaced ? styles.dimmed : ""}`}>
      <div className={css.fileMain}>
        <span className={css.fileName}>{row.filename}</span>
        <span className={styles.kpiNote}>
          {showCollection && (
            <>
              <span className="mono">{row.collection}</span> ·{" "}
            </>
          )}
          {formatBytes(row.size_bytes)} · {formatDateTime(row.finished_at ?? row.created_at)} ·{" "}
          {row.uploaded_by_user ?? <span className="mono">{row.uploaded_by}</span>}
        </span>
        {row.error && <span className={styles.error}>{row.error}</span>}
        {/* indexed, but the PDF's text has broken numbers (garbled OCR): answers from those pages may be refused */}
        {row.warning && !replaced && <span className={styles.warn}>⚠ {row.warning}</span>}
      </div>
      <div className={css.fileState}>{status}</div>
      <div className={css.fileActions}>
        {/* one Delete per file (it removes every version), on its newest row */}
        {canDelete && !replaced && (
          <ConfirmAction
            label="Delete"
            title="Delete this document?"
            confirmLabel="Delete document"
            action={deleteDocument.bind(null, row.collection, row.filename)}
            done={`${row.filename} deleted from ${row.collection}`}
          >
            <p>
              <strong>{row.filename}</strong> is removed from <span className={`mono ${styles.nowrap}`}>{row.collection}</span>{" "}
              completely: every version of it and its passages. Answers stop citing it at once. This can&apos;t be undone.
            </p>
          </ConfirmAction>
        )}
      </div>
    </li>
  );
}

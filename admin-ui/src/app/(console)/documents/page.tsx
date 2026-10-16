import Link from "next/link";

import { displayMessage } from "@/lib/api/api-error";
import { callApi, endSessionOn401 } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";
import { formatBytes, formatCount, formatDateTime } from "@/lib/format";
import { currentAccount } from "@/lib/session/current-account";
import { testersGoToChat } from "@/lib/session/testers-go-to-chat";

import AddDocument from "../chat/add-document";
import ConfirmAction from "../confirm-action";
import Pager from "../pager";
import styles from "../dashboard.module.css";
import { StatusErrorIcon, StatusOkIcon } from "../icons";
import { Problem } from "../widgets";
import { deleteCollection, deleteDocument } from "./actions";
import MoveCollectionButton from "./move-collection";
import ShareCollectionButton from "./share-collection";

export const metadata = { title: "Documents" };

const PAGE_SIZE = 100;

type Row = components["schemas"]["DocumentRow"];
type Collection = components["schemas"]["CollectionInfo"];

// Every uploaded file version and its indexing job, newest first, optionally one collection (?collection=).
// Everyone may upload new files; the super admin may also replace (in the upload dialog) and delete.
export default async function DocumentsPage({ searchParams }: PageProps<"/documents">) {
  await testersGoToChat(); // testers have only the Chat page
  const params = await searchParams;
  const one = (v: string | string[] | undefined) => (typeof v === "string" ? v.trim() : "");
  const collection = one(params.collection);
  const page = Math.max(1, Number.parseInt(one(params.page), 10) || 1);

  const [rows, collections, companies, me] = await Promise.all([
    callApi((api) =>
      api.GET("/v1/admin/documents", {
        params: { query: { collection: collection || undefined, limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE } },
      }),
    ),
    callApi((api) => api.GET("/v1/admin/collections")),
    callApi((api) => api.GET("/v1/admin/companies")),
    currentAccount(),
  ]);
  endSessionOn401(rows, collections, companies, me);
  const companyList = companies.ok ? companies.data.map((c) => ({ company_id: c.company_id, name: c.name })) : [];

  const isSuperAdmin = me.ok && me.data.role === "super_admin";
  const pageHref = (p: number) => {
    const q = new URLSearchParams();
    if (collection) q.set("collection", collection);
    if (p > 1) q.set("page", String(p));
    const s = q.toString();
    return s ? `/documents?${s}` : "/documents";
  };

  return (
    <>
      <header className={styles.header}>
        <h1>Documents</h1>
        {collections.ok && (
          <AddDocument
            collections={collections.data.map((c) => c.name)}
            initial={collection || undefined}
            label="Upload document"
            canReplace={isSuperAdmin}
            companies={companyList}
          />
        )}
      </header>

      {collections.ok && collections.data.length > 0 && (
        // One compact row per collection (was one box per company): owner order = each company (alphabetical), then
        // Global. A name is a link that lists only its files below (?collection=, shareable, Back works).
        <section aria-labelledby="collections-title" className={styles.card}>
          <div className={styles.cardHead}>
            <h2 id="collections-title" className={styles.panelTitle}>
              Collections
            </h2>
            <p className={styles.muted}>Click a name to list only its files.</p>
          </div>
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th scope="col">Collection</th>
                  <th scope="col">Belongs to</th>
                  <th scope="col" className={styles.number}>
                    Files
                  </th>
                  <th scope="col" className={styles.number}>
                    Passages
                  </th>
                  <th scope="col">Also shared with</th>
                  {isSuperAdmin && <th scope="col" className={styles.actionsCell}>{/* actions */}</th>}
                </tr>
              </thead>
              <tbody>
                {[...companyList, { company_id: null, name: "Global" }].flatMap((owner) =>
                  collections.data
                    .filter((c) => (c.company_id ?? null) === owner.company_id)
                    .map((c) => (
                      <CollectionRow
                        key={c.name}
                        c={c}
                        ownerName={owner.name}
                        open={c.name === collection}
                        canDelete={isSuperAdmin}
                        companies={companyList}
                      />
                    )),
                )}
              </tbody>
            </table>
          </div>
        </section>
      )}

      <section className={styles.card} aria-labelledby="files-title">
        <div className={styles.toolbar}>
          <div className={styles.inline}>
            <h2 id="files-title" className={styles.panelTitle}>
              {collection ? (
                <>
                  Files in <span className="mono">{collection}</span>
                </>
              ) : (
                "All files"
              )}
            </h2>
            {collection && (
              <Link href="/documents" className={styles.clear}>
                Show all collections
              </Link>
            )}
          </div>
          {rows.ok && <Pager page={page} count={rows.data.length} pageSize={PAGE_SIZE} noun="Files" href={pageHref} />}
        </div>
        {!rows.ok ? (
          <Problem message={displayMessage(rows.error)} />
        ) : rows.data.length === 0 ? (
          <p className={styles.muted}>
            {page > 1
              ? "No more documents."
              : collection
                ? "No documents in this collection yet. Upload one with the button above."
                : "No documents yet. Upload one with the button above."}
          </p>
        ) : (
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th scope="col">File and size</th>
                  {/* one collection chosen: the column would only repeat it */}
                  {!collection && <th scope="col">Collection</th>}
                  <th scope="col">Status</th>
                  <th scope="col" className={styles.number}>
                    Passages
                  </th>
                  <th scope="col">Uploaded, by</th>
                  {isSuperAdmin && <th scope="col" className={styles.actionsCell}>{/* actions */}</th>}
                </tr>
              </thead>
              <tbody>
                {markReplaced(rows.data).map(({ row, replaced }) => (
                  <DocumentRow
                    key={row.document_id}
                    row={row}
                    replaced={replaced}
                    canDelete={isSuperAdmin}
                    showCollection={!collection}
                  />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
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

function DocumentRow({
  row,
  replaced,
  canDelete,
  showCollection,
}: {
  row: Row;
  replaced: boolean;
  canDelete: boolean;
  showCollection: boolean;
}) {
  const status = replaced ? (
    <span className={styles.muted} title="A newer upload of this file replaced it; its passages are no longer searched">
      ○ Replaced
    </span>
  ) : row.job_status === "done" ? (
    <span className={`${styles.withIcon} ${styles.ok}`}>
      <StatusOkIcon /> Indexed
    </span>
  ) : row.job_status === "failed" ? (
    <span className={`${styles.withIcon} ${styles.error}`}>
      <StatusErrorIcon /> Failed
    </span>
  ) : (
    <span className={styles.warn}>◌ Indexing…</span>
  );

  return (
    <tr className={replaced ? styles.dimmed : undefined}>
      {/* size and uploader sit under the name / date (two fewer columns: the table fits without scrolling) */}
      <td className={styles.fileCell}>
        {row.filename}
        <div className={`${styles.kpiNote} ${styles.num}`}>{formatBytes(row.size_bytes)}</div>
        {row.error && <div className={styles.error}>{row.error}</div>}
      </td>
      {showCollection && (
        <td className={`mono ${styles.nowrap}`} translate="no">
          {row.collection}
        </td>
      )}
      <td className={styles.nowrap}>{status}</td>
      <td className={styles.number}>{replaced || row.chunks == null ? "–" : formatCount(row.chunks)}</td>
      <td className={styles.nowrap}>
        {formatDateTime(row.finished_at ?? row.created_at)}
        <div className={styles.kpiNote}>
          {row.uploaded_by_user ?? (
            <span className="mono" translate="no">
              {row.uploaded_by}
            </span>
          )}
        </div>
      </td>
      {canDelete && (
        <td className={styles.actionsCell}>
          {/* one Delete per file (it removes every version), on its newest row */}
          {!replaced && (
            <ConfirmAction
              label="Delete"
              title="Delete this document?"
              confirmLabel="Delete document"
              action={deleteDocument.bind(null, row.collection, row.filename)}
              done={`${row.filename} deleted from ${row.collection}`}
            >
              <p>
                <strong>{row.filename}</strong> is removed from{" "}
                <span className={`mono ${styles.nowrap}`}>{row.collection}</span> completely: every version of it and
                its passages. Answers stop citing it at once. This can&apos;t be undone.
              </p>
            </ConfirmAction>
          )}
        </td>
      )}
    </tr>
  );
}

// One collection as a table row: name (a link that filters the files), owner, counts, who else may use it, and for the
// super admin Move / Share / Delete. Delete only when it can go (empty and not from the server settings); otherwise
// the reason, in words. FastAPI checks both again.
function CollectionRow({
  c,
  ownerName,
  open,
  canDelete,
  companies,
}: {
  c: Collection;
  ownerName: string;
  open: boolean;
  canDelete: boolean;
  companies: { company_id: string; name: string }[];
}) {
  const empty = c.documents === 0 && c.chunks === 0;
  return (
    <tr className={open ? styles.rowOpen : undefined}>
      <td className={styles.nowrap}>
        <Link
          href={`/documents?collection=${encodeURIComponent(c.name)}`}
          className="mono"
          translate="no"
          aria-current={open ? "true" : undefined}
        >
          {c.name}
        </Link>
      </td>
      <td className={styles.ownerCell}>
        {ownerName}
        {c.company_id === null && <div className={styles.kpiNote}>any company&apos;s key may get it</div>}
      </td>
      <td className={styles.number}>{formatCount(c.documents)}</td>
      <td className={styles.number}>{formatCount(c.chunks)}</td>
      <td>
        {c.shared_with.length > 0 ? (
          c.shared_with.map((id) => companies.find((x) => x.company_id === id)?.name ?? id).join(", ")
        ) : (
          <span className={styles.muted}>–</span>
        )}
      </td>
      {canDelete && (
        <td className={styles.actionsCell}>
          <div className={styles.rowActions}>
            <MoveCollectionButton name={c.name} current={c.company_id ?? null} companies={companies} />
            {c.company_id && (
              <ShareCollectionButton
                name={c.name}
                owner={c.company_id}
                sharedWith={c.shared_with}
                companies={companies}
              />
            )}
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
        </td>
      )}
    </tr>
  );
}

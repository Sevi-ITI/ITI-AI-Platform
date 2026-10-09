import Link from "next/link";

import { displayMessage } from "@/lib/api/api-error";
import { callApi, endSessionOn401 } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";
import { formatBytes, formatCount, formatDateTime } from "@/lib/format";
import { currentAccount } from "@/lib/session/current-account";

import AddDocument from "../chat/add-document";
import ConfirmAction from "../confirm-action";
import Pager from "../pager";
import styles from "../dashboard.module.css";
import { Problem } from "../widgets";
import { deleteCollection, deleteDocument } from "./actions";
import MoveCollectionButton from "./move-collection";

export const metadata = { title: "Documents" };

const PAGE_SIZE = 100;

type Row = components["schemas"]["DocumentRow"];
type Collection = components["schemas"]["CollectionInfo"];

// Every uploaded file version and its indexing job, newest first, optionally one collection (?collection=).
// Everyone may upload new files; the super admin may also replace (in the upload dialog) and delete.
export default async function DocumentsPage({ searchParams }: PageProps<"/documents">) {
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
        // grouped by owner: each company (alphabetical), then Global
        <section aria-labelledby="collections-title" className={styles.card}>
          <h2 id="collections-title" className={styles.panelTitle}>
            Collections
          </h2>
          <div className={styles.collectionGroups}>
            {[...companyList, { company_id: null, name: "Global" }]
              .map((owner) => ({
                owner,
                own: collections.data.filter((c) => (c.company_id ?? null) === owner.company_id),
              }))
              .filter(({ own }) => own.length > 0)
              .map(({ owner, own }) => (
                <div key={owner.company_id ?? "global"} className={styles.collectionGroup}>
                  <span className={styles.groupLabel}>
                    {owner.name}
                    {owner.company_id === null && (
                      <span className={styles.muted}> (any company&apos;s key may be given these)</span>
                    )}
                  </span>
                  <div className={styles.collections}>
                    {own.map((c) => (
                      <CollectionChip key={c.name} c={c} canDelete={isSuperAdmin} companies={companyList} />
                    ))}
                  </div>
                </div>
              ))}
          </div>
        </section>
      )}

      <section className={styles.card} aria-label="Documents">
        <div className={styles.toolbar}>
          {/* Filters (a plain GET form: the filter lands in the URL (shareable, Back works), no JavaScript), then the pager */}
          <form action="/documents" className={styles.filters}>
            <label>
              <span>Collection</span>
              <select name="collection" defaultValue={collection}>
                <option value="">All collections</option>
                {collections.ok &&
                  collections.data.map((c) => (
                    <option key={c.name} value={c.name}>
                      {c.name}
                    </option>
                  ))}
              </select>
            </label>
            <button type="submit" className={styles.apply}>
              Apply filter
            </button>
            {collection && (
              <Link href="/documents" className={styles.clear}>
                Clear filter
              </Link>
            )}
          </form>
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
                  <th scope="col">File</th>
                  <th scope="col">Collection</th>
                  <th scope="col" className={styles.number}>
                    Size
                  </th>
                  <th scope="col">Status</th>
                  <th scope="col" className={styles.number}>
                    Passages
                  </th>
                  <th scope="col" className={styles.nowrap}>
                    Uploaded by
                  </th>
                  <th scope="col">Uploaded</th>
                  {isSuperAdmin && <th scope="col">{/* actions */}</th>}
                </tr>
              </thead>
              <tbody>
                {markReplaced(rows.data).map(({ row, replaced }) => (
                  <DocumentRow key={row.document_id} row={row} replaced={replaced} canDelete={isSuperAdmin} />
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

function DocumentRow({ row, replaced, canDelete }: { row: Row; replaced: boolean; canDelete: boolean }) {
  const status = replaced ? (
    <span className={styles.muted} title="A newer upload of this file replaced it; its passages are no longer searched">
      ○ Replaced
    </span>
  ) : row.job_status === "done" ? (
    <span className={styles.ok}>● Indexed</span>
  ) : row.job_status === "failed" ? (
    <span className={styles.error}>✕ Failed</span>
  ) : (
    <span className={styles.warn}>◌ Indexing…</span>
  );

  return (
    <tr className={replaced ? styles.dimmed : undefined}>
      <td className={styles.fileCell}>
        {row.filename}
        {row.error && <div className={styles.error}>{row.error}</div>}
      </td>
      <td className={`mono ${styles.nowrap}`} translate="no">
        {row.collection}
      </td>
      <td className={styles.number}>{formatBytes(row.size_bytes)}</td>
      <td className={styles.nowrap}>{status}</td>
      <td className={styles.number}>{replaced || row.chunks == null ? "–" : formatCount(row.chunks)}</td>
      <td className={styles.nowrap}>
        {row.uploaded_by_user ?? (
          <span className="mono" translate="no">
            {row.uploaded_by}
          </span>
        )}
      </td>
      <td className={styles.nowrap}>{formatDateTime(row.finished_at ?? row.created_at)}</td>
      {canDelete && (
        <td>
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

// One collection: its counts, and (super admin) Delete when it can go: empty and not from the server settings.
// Otherwise the reason it stays, in words. FastAPI checks both again.
function CollectionChip({
  c,
  canDelete,
  companies,
}: {
  c: Collection;
  canDelete: boolean;
  companies: { company_id: string; name: string }[];
}) {
  const empty = c.documents === 0 && c.chunks === 0;
  return (
    <div className={styles.collection}>
      <span>
        <span className="mono" translate="no">
          {c.name}
        </span>{" "}
        <span className={styles.muted}>
          {formatCount(c.documents)} {c.documents === 1 ? "file" : "files"}, {formatCount(c.chunks)} passages
        </span>
      </span>
      {canDelete && <MoveCollectionButton name={c.name} current={c.company_id ?? null} companies={companies} />}
      {canDelete &&
        (c.in_settings ? (
          <span className={styles.muted} title="Listed in ITI_COLLECTIONS: it would come back at the next restart">
            from server settings
          </span>
        ) : !empty ? (
          <span className={styles.muted} title="Delete its documents first">
            not empty
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
        ))}
    </div>
  );
}

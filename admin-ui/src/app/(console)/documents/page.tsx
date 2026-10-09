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
import { deleteDocument } from "./actions";

export const metadata = { title: "Documents" };

const PAGE_SIZE = 100;

type Row = components["schemas"]["DocumentRow"];

// Every uploaded file version and its indexing job, newest first, optionally one collection (?collection=).
// Everyone may upload new files; the super admin may also replace (in the upload dialog) and delete.
export default async function DocumentsPage({ searchParams }: PageProps<"/documents">) {
  const params = await searchParams;
  const one = (v: string | string[] | undefined) => (typeof v === "string" ? v.trim() : "");
  const collection = one(params.collection);
  const page = Math.max(1, Number.parseInt(one(params.page), 10) || 1);

  const [rows, collections, me] = await Promise.all([
    callApi((api) =>
      api.GET("/v1/admin/documents", {
        params: { query: { collection: collection || undefined, limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE } },
      }),
    ),
    callApi((api) => api.GET("/v1/admin/collections")),
    currentAccount(),
  ]);
  endSessionOn401(rows, collections, me);

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
          />
        )}
      </header>

      {collections.ok && collections.data.length > 0 && (
        <p className={styles.muted}>
          {collections.data
            .map((c) => `${c.name}: ${formatCount(c.documents)} files, ${formatCount(c.chunks)} passages`)
            .join(" · ")}
        </p>
      )}

      {/* A plain GET form: the filter lands in the URL (shareable, Back works), no JavaScript */}
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

      {rows.ok && (
        <Pager page={page} count={rows.data.length} pageSize={PAGE_SIZE} noun="Files" href={pageHref} />
      )}

      <section className={styles.card} aria-label="Documents">
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
                {rows.data.map((r) => (
                  <DocumentRow key={r.document_id} row={r} canDelete={isSuperAdmin} />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

    </>
  );
}

function DocumentRow({ row, canDelete }: { row: Row; canDelete: boolean }) {
  const status =
    row.job_status === "done" ? (
      <span className={styles.ok}>● Indexed</span>
    ) : row.job_status === "failed" ? (
      <span className={styles.error}>✕ Failed</span>
    ) : (
      <span className={styles.warn}>◌ Indexing…</span>
    );

  return (
    <tr>
      <td className={styles.fileCell}>
        {row.filename}
        {row.error && <div className={styles.error}>{row.error}</div>}
      </td>
      <td className={`mono ${styles.nowrap}`} translate="no">
        {row.collection}
      </td>
      <td className={styles.number}>{formatBytes(row.size_bytes)}</td>
      <td className={styles.nowrap}>{status}</td>
      <td className={styles.number}>{row.chunks == null ? "–" : formatCount(row.chunks)}</td>
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
          <ConfirmAction
            label="Delete"
            title="Delete this document?"
            confirmLabel="Delete document"
            action={deleteDocument.bind(null, row.collection, row.filename)}
            done={`${row.filename} deleted from ${row.collection}`}
          >
            <p>
              <strong>{row.filename}</strong> is removed from{" "}
              <span className={`mono ${styles.nowrap}`}>{row.collection}</span> completely: every version of it and its
              passages. Answers stop citing it at once. This can&apos;t be undone.
            </p>
          </ConfirmAction>
        </td>
      )}
    </tr>
  );
}

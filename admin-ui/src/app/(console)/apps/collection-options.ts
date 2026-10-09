// Plain helpers shared by the server page and the client dialogs (no "use client": a client module's functions
// can't be called while the server renders).

export type CollectionOption = { name: string; company_id: string | null }; // company_id null = Global
export type CompanyOption = { company_id: string; name: string };

/** What a key for `company` may be given: that company's collections and Global ones (FastAPI checks it too). */
export function usableBy(collections: CollectionOption[], company: string) {
  return collections.filter((c) => c.company_id === company || c.company_id === null);
}

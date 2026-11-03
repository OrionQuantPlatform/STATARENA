/** Bounded list contract. Complete-season consumers opt into full traversal. */
export async function readFixturePage(parameters, fetcher = fetch) {
  const query = new URLSearchParams(parameters);
  const response = await fetcher("/api/fixtures?" + query);
  const body = await response.json();
  if (!response.ok) {
    const error = new Error(body.error?.message || "Matchs indisponibles.");
    error.status = response.status;
    throw error;
  }
  if (!Array.isArray(body.data?.matches) || !body.pagination)
    throw new Error("Page de matchs invalide.");
  return body;
}
export async function allFixturePages(parameters, fetcher = fetch) {
  for (let attempt = 0; attempt < 2; attempt++) {
    const matches = [],
      seen = new Set();
    let cursor = null;
    try {
      do {
        const page = await readFixturePage(
          { ...parameters, limit: "100", ...(cursor ? { cursor } : {}) },
          fetcher,
        );
        matches.push(...page.data.matches);
        cursor = page.pagination.nextCursor;
        if (cursor && (seen.has(cursor) || seen.size >= 1000))
          throw new Error("Pagination de matchs incohérente.");
        if (cursor) seen.add(cursor);
      } while (cursor);
      return { data: { matches } };
    } catch (error) {
      if (error.status !== 409 || attempt === 1) throw error;
    }
  }
}

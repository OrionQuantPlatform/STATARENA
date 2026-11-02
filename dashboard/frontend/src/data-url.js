/** Include the deployment revision so shared caches never mix data releases. */
export const dataUrl = (path) => {
  const revision = process.env.NEXT_PUBLIC_DATA_REVISION;
  if (/^[a-f0-9]{40}$/i.test(revision || "")) {
    const relative =
      path === "dashboard-manifest.json"
        ? "computed/dashboard/index.json"
        : path === "football-manifest.json"
          ? "raw/index.json"
          : path;
    return `/data/${revision}/${relative}`;
  }
  return `/data/${path}`;
};

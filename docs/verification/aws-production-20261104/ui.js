// Called with real Playwright page and explicit, public SQL-derived targets.
const { frontend, api, selections: s, artifact } = OPTIONS;
const result = {
    views: [],
    events: [],
    violations: [],
    errors: [],
    missing: [],
    passed: false,
  },
  allowed = new URL(api).origin,
  site = new URL(frontend).origin;
const externalProvider =
  /(^|\.)(pitchapi\.dev|thesportsdb\.com|wikidata\.org|wikipedia\.org|openligadb\.de|uefa\.com|amazonaws\.com|githubusercontent\.com)$/i;
let phase = "bootstrap";
const safe = (u) =>
  u.origin === allowed || u.origin === site
    ? u.origin + u.pathname + (u.pathname === "/api/assets" ? "" : u.search)
    : u.origin + u.pathname;
page.on("pageerror", (e) =>
  result.errors.push({
    phase,
    error: e.name + ": " + String(e.message).slice(0, 160),
  }),
);
page.on("request", (r) => {
  const u = new URL(r.url()),
    type = r.resourceType(),
    structured = ["xhr", "fetch", "eventsource", "websocket"].includes(type);
  const ownApi =
    u.pathname.startsWith("/api/") &&
    u.origin !== allowed &&
    !(u.pathname === "/api/visitor-country" && u.origin === site);
  if (
    ownApi ||
    (structured &&
      (/^\/data(?:\/|$)/.test(u.pathname) || externalProvider.test(u.hostname)))
  )
    result.violations.push({ phase, type, url: safe(u) });
});
page.on("response", (r) => {
  const u = new URL(r.url());
  if (
    u.origin === allowed ||
    (u.origin === site &&
      (u.pathname.startsWith("/api/") || u.pathname.startsWith("/data/")))
  ) {
    const headers = r.headers();
    result.events.push({
      phase,
      path: u.pathname,
      origin: u.origin,
      method: r.request().method(),
      status: r.status(),
      cache: headers["x-cache"] || null,
      encodedLength: headers["content-length"] || null,
      ttfbMs: r.request().timing().responseStart,
    });
  }
});
const route = (path, p) =>
  site +
  path +
  "?" +
  new URLSearchParams(Object.entries(p || {}).filter(([, v]) => v != null));
const text = async (loc) =>
  (await loc.first().innerText({ timeout: 1500 }))
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, 240);
const successPath = (row, path) =>
  row.events.some(
    (r) => r.path === path && r.status === 200 && r.origin === allowed,
  );
async function visit(
  name,
  path,
  { selector, needle, expectPath, action, check } = {},
) {
  phase = name;
  const before = result.events.length,
    start = Date.now(),
    row = { name, url: path, ok: false };
  result.views.push(row);
  try {
    const resp = await page.goto(path, {
      waitUntil: "domcontentloaded",
      timeout: 35000,
    });
    row.status = resp.status();
    if (row.status >= 400) throw Error("front HTTP " + row.status);
    if (selector) {
      const loc = page.locator(selector).first();
      await loc.waitFor({ state: "visible", timeout: 40000 });
      row.visible = await text(loc);
    }
    if (needle)
      await page
        .getByText(needle, { exact: false })
        .first()
        .waitFor({ state: "visible", timeout: 30000 });
    if (action) await action(row);
    row.events = result.events.slice(before);
    if (expectPath && !successPath(row, expectPath))
      throw Error("missing successful API request " + expectPath);
    if (check && !(await check(row)))
      throw Error("rendered state did not satisfy view contract");
    row.ok = true;
  } catch (e) {
    row.error = String(e.message).slice(0, 520);
  }
  row.events = result.events.slice(before);
  row.elapsedMs = Date.now() - start;
  if (
    !row.ok ||
    ["match-overview-and-details", "mobile-archives"].includes(name)
  ) {
    await page
      .screenshot({ path: artifact + "/" + name + ".png", timeout: 8000 })
      .catch(() => {});
  }
  return row;
}
await page.setViewportSize({ width: 1440, height: 1000 });
const initial = await page.goto(site + "/", {
  waitUntil: "domcontentloaded",
  timeout: 35000,
});
result.frontendStatus = initial.status();
if (initial.status() >= 400) {
  result.errors.push({
    phase,
    error: "Production frontend HTTP " + initial.status(),
  });
  return result;
}
const part = s.partition,
  match = s.match,
  player = s.player;
const scope = part
  ? { season: part.season, league: part.league_id, focus: "all" }
  : {};
await visit("home", route("/", scope), {
  selector: ".home-motw",
  expectPath: "/api/dashboard/manifest",
  check: async () => /\d/.test(await page.locator("main").innerText()),
});
await visit("match-list", route("/matchs/", { ...scope, tab: "results" }), {
  selector: ".match-row",
  check: async (row) =>
    row.visible.length > 2 &&
    row.events.some(
      (e) => e.path === "/api/seasons/partition" && e.status === 200,
    ),
});
if (s.upcoming)
  await visit(
    "calendar",
    route("/calendrier/", {
      ...scope,
      season: s.upcoming.season,
      league: s.upcoming.league_id,
      week: s.upcoming.day,
    }),
    {
      selector: "main",
      check: async () => {
        await page.waitForURL(/\/matchs\/?\?.*tab=upcoming/, {
          timeout: 10000,
        });
        await page
          .locator(".match-row,.matchday-schedule")
          .first()
          .waitFor({ timeout: 25000 });
        return true;
      },
    },
  );
else result.missing.push("calendar: published upcoming fixture");
await visit("player-ranking", route("/classement-joueurs/", scope), {
  selector: ".rank-list li,.podium a,.rank-board a",
  check: async (row) => row.visible.length > 2,
});
await visit("player-directory", route("/joueurs/", scope), {
  selector: ".data-table tbody tr",
  check: async (row) => row.visible.length > 2,
});
if (player)
  await visit(
    "player-profile",
    route("/joueurs/", { ...scope, id: player.player_id }),
    {
      needle: player.name,
      check: async () => {
        await page
          .locator(
            ".season-player-figures,.season-player-profile,.player-trophy-rail",
          )
          .first()
          .waitFor({ timeout: 15000 });
        return true;
      },
    },
  );
else result.missing.push("player-profile");
if (match)
  await visit(
    "club-profile",
    route("/clubs/", { ...scope, id: match.home_id }),
    {
      needle: match.home_name,
      selector: ".club-overview-panel,.club-figures",
      check: async (row) => row.visible.length > 2,
    },
  );
else result.missing.push("club-profile");
await visit(
  "competitions",
  route("/competitions/", { ...scope, id: part?.league_id }),
  {
    selector: ".data-table tbody tr,.match-row,.matchday-schedule",
    needle: part?.name,
  },
);
if (s.cup)
  await visit(
    "cup",
    route("/competitions/", { ...scope, id: s.cup.id, edition: s.cup.season }),
    {
      selector: ".cup-match",
      check: async (row) =>
        row.events.some(
          (e) =>
            e.status === 200 &&
            [
              "/api/cup-snapshot",
              "/api/cup-table",
              "/api/open-cups",
              "/api/openligadb",
            ].includes(e.path),
        ),
    },
  );
else result.missing.push("cup");
await visit("archives", route("/archives/", { as: s.archiveSeason }), {
  selector: ".archive-results tbody tr",
  expectPath: "/api/archives/season",
  check: async (row) => row.visible.length > 8,
});
if (match && part && s.alternatePartition) {
  const alt = s.alternatePartition;
  await visit(
    "match-overview-and-details",
    route("/matchs/", {
      ...scope,
      league: alt.league_id,
      season: alt.season,
      id: match.id,
      sourceSeason: part.season,
      competition: part.league_id,
      tab: "results",
    }),
    {
      selector: ".match-scoreboard",
      needle: match.home_name,
      action: async (row) => {
        const summary = "/api/matches/" + match.id + "/summary",
          base = "/api/pitchapi/matches/" + match.id,
          archive = "/api/archive/matches/" + match.id;
        const prior = result.events.filter((e) => e.phase === phase);
        if (!prior.some((e) => e.path === summary && e.status === 200))
          throw Error(
            "dedicated overview endpoint did not supply remote match",
          );
        if (
          prior.some((e) => e.path.startsWith(base + "/") || e.path === archive)
        )
          throw Error(
            "heavy family/whole archive requested before interaction",
          );
        for (const [family, label, selector] of [
          ["stats", "Statistiques", ".stats-board"],
          ["shots", "Tirs & xG", ".shot-minute,.shot-xg"],
        ]) {
          const request = page.waitForResponse(
            (r) =>
              new URL(r.url()).origin === allowed &&
              new URL(r.url()).pathname === base + "/" + family,
            { timeout: 30000 },
          );
          const toggle = page.getByRole("tab", { name: label, exact: true });
          const [observed] = await Promise.all([
            request,
            toggle.click({ timeout: 12000 }),
          ]);
          if (observed.status() !== 200)
            throw Error("detail " + family + " HTTP " + observed.status());
          await page
            .locator(selector)
            .first()
            .waitFor({ state: "visible", timeout: 30000 });
        }
        if (result.events.some((e) => e.phase === phase && e.path === archive))
          throw Error(
            "whole-match archive fallback during successful lazy detail",
          );
      },
    },
  );
} else
  result.missing.push(
    "remote summary/lazy detail (second published scope and rich match required)",
  );
await page.setViewportSize({ width: 390, height: 844 });
await visit("mobile-archives", route("/archives/", { as: s.archiveSeason }), {
  selector: ".archive-results tbody tr",
  expectPath: "/api/archives/season",
  check: async () =>
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth + 2,
    ),
});
result.passed =
  result.views.length > 0 &&
  result.views.every((r) => r.ok) &&
  !result.violations.length &&
  !result.errors.length &&
  !result.missing.length;
return result;

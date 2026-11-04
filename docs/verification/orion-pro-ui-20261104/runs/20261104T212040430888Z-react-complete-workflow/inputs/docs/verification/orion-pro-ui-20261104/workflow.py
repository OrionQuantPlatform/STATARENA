"""Real-browser assertions prepared from the protocol; no application/cache injection."""
import json
import re
from urllib.parse import parse_qs, urlsplit

HEAVY = re.compile(r"\bfootball\.(shots|match_heatmaps|match_heatmap_cells|pass_networks|pass_network_nodes|pass_network_edges)\b", re.I)


class BrowserWorkflow:
    def __init__(self, *, cli, result_value, fixture, report, run, artifacts, case, http_json, base):
        self.cli, self.result_value, self.fixture = cli, result_value, fixture
        self.report, self.run, self.artifacts = report, run, artifacts
        self.case, self.http_json, self.base = case, http_json, base
        self.steps, self.document = 0, None
        self.tokens = report["tokensBefore"]
        self.a, self.b, self.c = [self.tokens[season] for season in ("2024/2025", "2025/2026", "2026/2027")]

    def snapshot(self, label):
        path = self.artifacts / (label + ".snapshot.yml")
        self.cli("snapshot", "--filename", path)
        return path.read_text()

    def capture(self, label, screenshot=False):
        self.steps += 1
        label = f"{self.steps:02d}-{label}"
        state = self.result_value(self.cli("run-code", "--filename", self.base / "browser_state.js"))
        if self.document is None: self.document = state["documentIdentity"]
        assert state["documentIdentity"] == self.document, "A document reload cannot establish retained in-app cache reuse"
        (self.run / (label + ".json")).write_text(json.dumps(state, indent=2) + "\n")
        self.snapshot(label)
        if screenshot: self.cli("screenshot", "--filename", self.artifacts / (label + ".png"), "--full-page")
        self.report.setdefault("uiPhases", []).append({"label": label, "evidence": label + ".json", "url": state["url"], "rows": len(state["rows"]), "documentIdentity": state["documentIdentity"], "requestCount": len(state["proof"]["requests"])})
        return state

    def wait(self, expression):
        self.cli("run-code", "async (page) => { await page.waitForFunction(() => (" + expression + "), null, { timeout: 15000 }); return { ready: true }; }", timeout=25)

    def wait_response(self, path, token):
        self.cli("run-code", "async (page) => { const end = Date.now() + 15000; while (Date.now() < end) { const found = page.__orionUI.responses.find(r => new URL(r.url).pathname === " + json.dumps(path) + " && new URL(r.url).searchParams.get('v') === " + json.dumps(token) + " && typeof r.body === 'string'); if (found) return { status: found.status }; await new Promise(resolve => setTimeout(resolve, 25)); } throw Error('Expected real HTTP response body not completed'); }", timeout=25)

    def click_named(self, role, name):
        snapshot = self.snapshot("before-" + str(self.steps) + "-" + role)
        line = next((line for line in snapshot.splitlines() if re.search(r"\b" + role + " " + re.escape(json.dumps(name, ensure_ascii=False)), line)), None)
        assert line, f"No {role} {name!r} in fresh DOM snapshot"
        assert "[disabled]" not in line, f"{name} unexpectedly disabled"
        reference = re.search(r"\[ref=(e\d+)\]", line)
        assert reference, line
        self.cli("click", reference.group(1))

    def click_row(self, public_id):
        snapshot = self.snapshot("before-row-" + public_id)
        lines = snapshot.splitlines()
        for index, line in enumerate(lines):
            if re.search(r"/url: .*\bid=" + public_id + r"(?:&|$)", line):
                previous = lines[index - 1]
                reference = re.search(r"\[ref=(e\d+)\]", previous)
                if reference:
                    self.cli("click", reference.group(1))
                    return
        raise AssertionError(f"No real match link {public_id} in fresh snapshot")

    def season(self, season):
        snapshot = self.snapshot("before-season-" + season.replace("/", "-"))
        line = next((line for line in snapshot.splitlines() if 'combobox "Saison"' in line), None)
        assert line, "Existing accessible Saison control is required"
        reference = re.search(r"\[ref=(e\d+)\]", line)
        self.cli("select", reference.group(1), season)
        target = "m_000005" if season == "2026/2027" else "m_000004" if season == "2025/2026" else "m_000001"
        self.wait("!!document.querySelector('.match-row[href*=\"id=" + target + "\"]')")

    def results(self, *, refresh=False):
        self.click_named("link", "Résultats")
        self.wait("!!document.querySelector('.match-row')")
        if refresh:
            self.click_named("button", "Actualiser")
            self.wait("!!document.querySelector('.match-row')")

    @staticmethod
    def ids(state):
        return [parse_qs(urlsplit(row["href"]).query)["id"][0] for row in state["rows"]]

    @staticmethod
    def requests(state, path, token=None):
        return [request for request in state["proof"]["requests"] if request["method"] == "GET" and urlsplit(request["url"]).path == path and (token is None or parse_qs(urlsplit(request["url"]).query).get("v") == [token])]

    @staticmethod
    def response(state, path, token):
        responses = [response for response in state["proof"]["responses"] if response["method"] == "GET" and urlsplit(response["url"]).path == path and parse_qs(urlsplit(response["url"]).query).get("v") == [token]]
        assert responses, (path, token)
        response = responses[-1]
        assert response["status"] == 200 and "immutable" in response["headers"].get("cache-control", ""), response
        assert response["headers"].get("etag"), response
        return response

    def run_all(self):
        self.report["activeCase"] = "cursor_pages_30_30_1"
        first = self.capture("page-1", screenshot=True)
        expected_first = ["m_000001", "m_000002", *[f"m_{index:06d}" for index in range(6, 34)]]
        assert self.ids(first) == expected_first, self.ids(first)
        initial_traces = self.http_json("/__e2e__/traces")["requests"]
        assert not any(HEAVY.search(query["sql"]) for request in initial_traces for query in request["sql"])
        self.click_named("button", "Suivants")
        self.wait("!!document.querySelector('.match-row[href*=\"id=m_000034\"]')")
        second = self.capture("page-2")
        assert self.ids(second) == [f"m_{index:06d}" for index in range(34, 64)], self.ids(second)
        self.click_named("button", "Suivants")
        self.wait("document.querySelectorAll('.match-row').length === 1 && !!document.querySelector('.match-row[href*=\"id=m_000003\"]')")
        third = self.capture("page-3", screenshot=True)
        assert self.ids(third) == ["m_000003"]
        snapshot = self.snapshot("third-disabled-next")
        assert re.search(r'button "Suivants"[^\n]*\[disabled\]', snapshot), snapshot
        traversed = self.ids(first) + self.ids(second) + self.ids(third)
        assert len(traversed) == len(set(traversed)) == 61
        fixture_gets = self.requests(third, "/api/fixtures", self.a)
        assert len(fixture_gets) == 3, fixture_gets
        assert all(parse_qs(urlsplit(request["url"]).query).get("limit") == ["30"] for request in fixture_gets)
        bodies = [response for response in third["proof"]["responses"] if urlsplit(response["url"]).path == "/api/fixtures" and response["status"] == 200]
        assert [len(json.loads(response["body"])["data"]["matches"]) for response in bodies] == [30, 30, 1]
        for previous, following in zip(bodies, fixture_gets[1:]):
            cursor = json.loads(previous["body"])["pagination"]["nextCursor"]
            assert parse_qs(urlsplit(following["url"]).query)["cursor"] == [cursor]
        self.case("cursor_pages_30_30_1", "pass", counts=[30, 30, 1], uniqueIds=61, requests=fixture_gets)

        self.report["activeCase"] = "visited_page_cache"
        self.click_named("button", "Précédents")
        self.wait("!!document.querySelector('.match-row[href*=\"id=m_000034\"]')")
        self.click_named("button", "Précédents")
        self.wait("!!document.querySelector('.match-row[href*=\"id=m_000001\"]')")
        returned = self.capture("visited-page-1")
        assert self.ids(returned) == expected_first
        assert len(self.requests(returned, "/api/fixtures", self.a)) == 3
        assert all(parse_qs(urlsplit(row["href"]).query).get("v") == [self.a] for row in returned["rows"])
        self.case("visited_page_cache", "pass", fixturesGET=3, renderedRows=30, documentIdentity=self.document)

        self.report["activeCase"] = "summary_lightweight"
        summary_path, shots_path = "/api/matches/m_000001/summary", "/api/pitchapi/matches/m_000001/shots"
        self.click_row("m_000001")
        self.wait("!!document.querySelector('.match-scoreboard')")
        overview = self.capture("A-summary", screenshot=True)
        assert parse_qs(urlsplit(overview["url"]).query).get("v") == [self.a]
        assert len(self.requests(overview, summary_path, self.a)) == 1
        assert not self.requests(overview, shots_path)
        assert "Shared team v1" in " ".join(overview["scoreboard"])
        self.response(overview, summary_path, self.a)
        trace = self.http_json("/__e2e__/traces")
        assert not any(HEAVY.search(query["sql"]) for request in trace["requests"] for query in request["sql"])
        self.case("summary_lightweight", "pass", summaryGET=1, shotsGET=0, sqlCount=sum(len(request["sql"]) for request in trace["requests"]))

        self.report["activeCase"] = "shots_explicit_zero_meters_goal"
        self.click_named("tab", "Tirs & xG")
        self.wait("document.querySelectorAll('circle.shot-point').length === 1")
        shots = self.capture("A-shots-zero-metres", screenshot=True)
        assert len(self.requests(shots, shots_path, self.a)) == 1
        point = shots["points"][0]
        assert (float(point["cx"]), float(point["cy"]), float(point["r"])) == (330, 219, 6), point
        assert re.search(r"\bBut\b", point["label"]) and re.search(r"xG\s*:\s*0(?:\D|$)", point["label"]), point
        assert any(re.search(r"^\s*0(?:[,.]0+)?\s*xG\s*$", text) for text in shots["shotXg"]), shots["shotXg"]
        typed = json.loads(self.response(shots, shots_path, self.a)["body"])["data"]["periods"][0]["shots"][0]
        assert typed["expected_goals"] == typed["expected_goals_on_target"] == 0
        assert typed["event_type"] == "" and typed["is_goal"] is True and (typed["x"], typed["y"]) == (52.5, 34)
        self.case("shots_explicit_zero_meters_goal", "pass", typed=typed, actualSVG=point)
        self.report["activeCase"] = "same_detail_cache"
        self.click_named("tab", "Vue d’ensemble")
        self.wait("!document.querySelector('circle.shot-point')")
        self.click_named("tab", "Tirs & xG")
        self.wait("!!document.querySelector('circle.shot-point')")
        repeated = self.capture("A-shots-cache")
        assert len(self.requests(repeated, shots_path, self.a)) == 1
        assert len(self.requests(repeated, summary_path, self.a)) == 1
        self.case("same_detail_cache", "pass", summaryGET=1, shotsGET=1)

        self.report["activeCase"] = "mobile_operable"
        self.cli("resize", "390", "844")
        mobile_shots = self.capture("mobile-shots", screenshot=True)
        assert mobile_shots["viewport"]["width"] == 390
        assert mobile_shots["viewport"]["scrollWidth"] <= 391, mobile_shots["viewport"]
        self.results(refresh=True)
        self.wait("document.querySelectorAll('.match-row').length === 30")
        mobile_list = self.capture("mobile-list", screenshot=True)
        assert mobile_list["viewport"]["scrollWidth"] <= 391, mobile_list["viewport"]
        self.click_named("button", "Suivants")
        self.wait("!!document.querySelector('.match-row[href*=\"id=m_000034\"]')")
        self.click_named("button", "Précédents")
        self.wait("!!document.querySelector('.match-row[href*=\"id=m_000001\"]')")
        self.case("mobile_operable", "pass", viewport=mobile_list["viewport"], pager="Actual next/previous clicks completed at390px", shotCoordinates=mobile_shots["points"])
        self.cli("resize", "1440", "1000")

        self.report["activeCase"] = "independent_C_cache"
        self.season("2026/2027")
        self.click_row("m_000005")
        self.wait("!!document.querySelector('.match-scoreboard')")
        c_before = self.capture("C-before-publication")
        c_summary_path, c_shots_path = "/api/matches/m_000005/summary", "/api/pitchapi/matches/m_000005/shots"
        assert len(self.requests(c_before, c_summary_path, self.c)) == 1
        assert not self.requests(c_before, c_shots_path), "C summary must remain lightweight"
        self.response(c_before, c_summary_path, self.c)
        self.results(refresh=True)
        self.report["activeCase"] = "nullable_profile_rendering"
        self.season("2025/2026")
        self.click_row("m_000004")
        self.wait("!!document.querySelector('.match-scoreboard')")
        b_state = self.capture("B-null-profile", screenshot=True)
        b_response = json.loads(self.response(b_state, "/api/matches/m_000004/summary", self.b)["body"])
        assert b_response["data"]["match"]["away"]["name"] is None, b_response
        assert re.search(r"non renseign|inconnu|indisponible", " ".join(b_state["scoreboard"]), re.I), b_state["scoreboard"]
        assert not b_state["proof"]["pageErrors"], b_state["proof"]["pageErrors"]
        self.case("nullable_profile_rendering", "pass", apiName=None, scoreboard=b_state["scoreboard"])
        self.report["activeCase"] = "published_correction"
        self.results(refresh=True)
        self.season("2024/2025")
        self.click_row("m_000001")
        self.wait("!!document.querySelector('.match-scoreboard')")
        self.click_named("tab", "Tirs & xG")
        self.wait("!!document.querySelector('circle.shot-point')")
        before = self.capture("A-open-during-publication")
        assert len(self.requests(before, summary_path, self.a)) == 1
        assert len(self.requests(before, shots_path, self.a)) == 1
        self.report["correction"] = self.fixture.correct()
        current_manifest = self.http_json("/api/dashboard/manifest")
        (self.run / "manifest-after.json").write_text(json.dumps(current_manifest, indent=2) + "\n")
        after_tokens = {edition["season"]: edition["representationToken"] for edition in current_manifest["editions"]}
        self.report["tokensAfter"] = after_tokens
        assert after_tokens["2024/2025"] != self.a and after_tokens["2026/2027"] == self.c
        still_open = self.capture("A-stays-frozen-after-publication")
        assert (still_open["scoreboard"], still_open["points"], still_open["shotXg"]) == (before["scoreboard"], before["points"], before["shotXg"])
        self.results(refresh=True)
        # Actualiser is a real user action; wait for its new token to reach match links.
        a_new = after_tokens["2024/2025"]
        self.wait("[...document.querySelectorAll('.match-row')].some(row => new URL(row.href).searchParams.get('v') === " + json.dumps(a_new) + ")")
        self.click_row("m_000001")
        self.wait("document.querySelector('.match-scoreboard')?.textContent.includes('Shared team corrected')")
        self.click_named("tab", "Tirs & xG")
        self.wait("document.querySelector('.shot-xg')?.textContent.includes('0,67') || document.querySelector('.shot-xg')?.textContent.includes('0.67')")
        corrected = self.capture("A-latest-corrected", screenshot=True)
        assert parse_qs(urlsplit(corrected["url"]).query)["v"] == [a_new]
        new_typed = json.loads(self.response(corrected, shots_path, a_new)["body"])["data"]["periods"][0]["shots"][0]
        assert new_typed["expected_goals"] == 0.67 and new_typed["player"]["name"] == "Shared striker corrected", new_typed
        assert self.response(corrected, summary_path, a_new)["headers"]["etag"] != self.response(before, summary_path, self.a)["headers"]["etag"]
        self.case("published_correction", "pass", oldToken=self.a, newToken=a_new, currentShot=new_typed)

        self.report["activeCase"] = "old_A_pinned"
        # Breadcrumb pushed the latest list after old A. Going back twice uses
        # actual browser history, retaining the same JS document and client cache.
        self.cli("go-back")
        self.wait("!!document.querySelector('.match-row')")
        self.cli("go-back")
        self.wait("document.querySelector('.match-scoreboard')?.textContent.includes('Shared team v1') && !!document.querySelector('circle.shot-point')")
        old_again = self.capture("A-old-history-cache", screenshot=True)
        assert parse_qs(urlsplit(old_again["url"]).query)["v"] == [self.a]
        assert (old_again["scoreboard"], old_again["points"], old_again["shotXg"]) == (before["scoreboard"], before["points"], before["shotXg"])
        assert len(self.requests(old_again, summary_path, self.a)) == len(self.requests(old_again, shots_path, self.a)) == 1
        self.case("old_A_pinned", "pass", summaryGET=1, shotsGET=1, unchangedDOM=True, documentIdentity=self.document)
        self.report["activeCase"] = "independent_C_cache"
        c_counts = (len(self.requests(old_again, c_summary_path, self.c)), len(self.requests(old_again, c_shots_path, self.c)))
        for _ in range(4): self.cli("go-back")
        self.wait("document.querySelector('.match-scoreboard')?.textContent.includes('Team 3 v1')")
        c_again = self.capture("C-independent-history-cache", screenshot=True)
        assert parse_qs(urlsplit(c_again["url"]).query)["v"] == [self.c]
        assert c_again["scoreboard"] == c_before["scoreboard"]
        assert c_counts == (len(self.requests(c_again, c_summary_path, self.c)), len(self.requests(c_again, c_shots_path, self.c)))
        assert c_counts == (1, 0), c_counts
        self.case("independent_C_cache", "pass", tokenUnchanged=True, summaryGET=1, shotsGET=0, documentIdentity=self.document)

        self.report["activeCase"] = "network_and_sql_boundaries"
        proof = c_again["proof"]
        forbidden = [request for request in proof["requests"] if re.search(r"/(?:data|api/(?:seasons|status|leagues|openligadb|openfootball|nations-results|stadium))(?:/|\?|$)", urlsplit(request["url"]).path)]
        failures = [response for response in proof["responses"] if response["status"] >= 400]
        assert not forbidden and not failures and not proof["external"] and not proof["failures"] and not proof["pageErrors"], {"forbidden": forbidden, "badStatuses": failures, "external": proof["external"], "requestFailures": proof["failures"], "pageErrors": proof["pageErrors"]}
        assert not [entry for entry in proof["console"] if entry["type"] == "error"], proof["console"]
        traces = self.http_json("/__e2e__/traces")
        sql = [query for request in traces["requests"] for query in request["sql"]]
        assert traces["externalAttempts"] == 0
        assert not any(re.search(r"\b\w+_current\b", query["sql"], re.I) for query in sql)
        # All network heavy reads must be the explicit lazy shots endpoint.
        assert all("/shots?" in request["path"] for request in traces["requests"] if any(HEAVY.search(query["sql"]) for query in request["sql"]))
        data_gets = [request for request in proof["requests"] if urlsplit(request["url"]).path.startswith("/api/")]
        self.case("network_and_sql_boundaries", "pass", browserApiGET=len(data_gets), backendRequests=len(traces["requests"]), sqlQueries=len(sql), externalAttempts=0, unexpectedFailures=0)

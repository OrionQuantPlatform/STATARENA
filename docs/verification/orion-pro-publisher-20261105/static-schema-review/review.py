#!/usr/bin/env python3
"""Text/AST-only inventory; never imports the harness or a database driver."""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
BASE = HERE.parent
MODEL = ROOT / "docs/architecture/orion-plan-20261104/target-schema.proposed.json"
MODEL_SHA = "18da43f940870b7a3a3cb49323c847dd5e5174e5eea1f8ff0c8a159cf373cb08"
PUBLISHER = ROOT / "dashboard/scripts/orion_pro_publish.py"
HARNESSES = [
    BASE / name
    for name in [
        "publisher_oracles.py", "typed_inputs.py", "publisher_workflow.py",
        "publisher_driver.py", "publisher_worker.py", "workflow_budget.py",
    ]
] + [
    ROOT / "docs/verification/orion-pro-readers-20261104/fixture.py",
    ROOT / "docs/verification/orion-pro-pilot-20261104/fixtures.py",
    ROOT / "docs/verification/orion-pro-pilot-20261104/harness.py",
]
SUPPORT = [
    ROOT / "dashboard/backend/migrations/012_orion_pro_domain.sql",
    ROOT / "dashboard/backend/migrations/013_orion_pro_integrity.sql",
    ROOT / "dashboard/backend/services/orion-pro.js",
    ROOT / "dashboard/backend/services/relational-core.js",
    ROOT / "dashboard/backend/services/postgres.js",
    ROOT / "dashboard/backend/aws-app.js",
    ROOT / "dashboard/scripts/orion_pro_migrate.py",
    ROOT / "dashboard/scripts/orion_pro_integrity.py",
    BASE / "publisher_http_server.mjs",
]
PILOT_USED = {"__init__", "_log", "_row", "_insert", "_begin", "_generation", "_replace", "_reject", "_record"}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def emit(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def quoted_list(names):
    return ", ".join('"' + name + '"' for name in names)


def relation(name):
    return ".".join('"' + part + '"' for part in name.split("."))


def literal_values(node):
    if isinstance(node, ast.Constant):
        return [node.value]
    if isinstance(node, ast.IfExp):
        return literal_values(node.body) + literal_values(node.orelse)
    return []


def raw_row_table(site):
    """Explicit, manually traced bindings. This is not general type inference."""
    if site["reachability"] == "unreachable_pilot_scenarios":
        return None
    base, key, fn = site["base"], site.get("key"), site["function"]
    filename = Path(site["source"]).name
    for stem, table in [
        ("match_rows", "football.matches"), ("editions", "football.competition_seasons"),
        ("team_profiles", "football.team_profile_versions"), ("player_profiles", "football.player_profile_versions"),
        ("coverages", "ingest.match_coverage"), ("shot_rows", "football.shots"), ("scores", "football.match_scores"),
    ]:
        if re.match(r"(?:self|inputs|self\.inputs)\." + stem + r"\[", base):
            return table
    if re.match(r"(?:self|inputs|self\.inputs)\.ids\['teams'\]\[", base) or base == "teams[0]":
        return "football.teams"
    if re.match(r"(?:self|inputs|self\.inputs)\.ids\['players'\]\[", base):
        return "football.players"
    if base.startswith("self.sides[") and base.count("[") >= 2:
        return "football.match_teams"
    if re.fullmatch(r"sides\[(?:'home'|'away'|side)\]", base):
        return "football.match_teams"
    mapping = {}
    if filename == "typed_inputs.py":
        mapping = {
            "prepare_inputs": {"b": "football.matches", "team": "football.teams", "player": "football.players", "e": "football.competition_seasons"},
            "input_oracle": {"m": "football.matches", "e": "football.competition_seasons"},
            "admission": {"m": "football.matches", "e": "football.competition_seasons", "coverage": "ingest.match_coverage", "shot": "football.shots"},
            "mark_dirty": {"e": "football.competition_seasons"},
            "negative_input": {"changed": "football.matches"},  # accesses occur only in the draft branch
        }.get(fn, {})
    elif filename == "publisher_oracles.py" and fn == "expected_products":
        mapping = {"m": "football.matches", "edition": "football.competition_seasons"}
    elif filename == "fixture.py":
        if fn == "prepare":
            mapping = {"src": "ingest.sources", "other": "ingest.sources", "dataset": "ingest.source_datasets",
                       "other_dataset": "ingest.source_datasets", "record": "ingest.source_records", "provider_record": "ingest.source_records",
                       "other_record": "ingest.source_records", "p": "football.players", "player": "football.players",
                       "profile": "football.player_profile_versions", "competition": "football.competitions",
                       "edition": "football.competition_seasons", "match": "football.matches"}
            if base == "t" and key in {"id", "slug"}:
                return "football.teams"  # other t accesses belong to the model-metadata loop
        elif fn == "build":
            mapping = {"edition": "football.competition_seasons", "m": "football.matches", "b": "analytics.aggregation_builds"}
        elif fn == "describe":
            mapping = {"v": "football.competition_seasons", "m": "football.matches"}
    elif filename == "fixtures.py" and fn == "_record":
        mapping = {"document": "ingest.source_documents"}
    return mapping.get(base)


class Inventory(ast.NodeVisitor):
    def __init__(self, path, tables):
        self.path = str(path.relative_to(ROOT))
        self.tables = tables
        self.function = "<module>"
        self.accesses, self.sql, self.typed = [], [], []

    def context(self, node):
        if self.path.endswith("orion-pro-pilot-20261104/fixtures.py"):
            reach = "inherited_helper" if self.function in PILOT_USED else "unreachable_pilot_scenarios"
        elif self.path.endswith("orion-pro-readers-20261104/fixture.py"):
            reach = "setup_input" if self.function in {"prepare", "describe"} else "overridden_or_unused_reader_hooks"
        else:
            reach = "setup_or_future_workflow"
        return {"source": self.path, "line": node.lineno, "function": self.function, "reachability": reach}

    def visit_FunctionDef(self, node):
        previous = self.function
        self.function = node.name
        self.generic_visit(node)
        self.function = previous

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Subscript(self, node):
        if isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, (str, int)):
            self.accesses.append({**self.context(node), "expression": ast.unparse(node), "base": ast.unparse(node.value),
                                  "key": node.slice.value, "kind": "string_key" if isinstance(node.slice.value, str) else "integer_index"})
        else:
            self.accesses.append({**self.context(node), "expression": ast.unparse(node), "base": ast.unparse(node.value),
                                  "keyExpression": ast.unparse(node.slice), "kind": "dynamic_key_or_slice"})
        self.generic_visit(node)

    def visit_Call(self, node):
        if isinstance(node.func, ast.Attribute) and node.args:
            if node.func.attr in {"execute", "executemany", "copy"}:
                first = node.args[0]
                literal = first.value if isinstance(first, ast.Constant) and isinstance(first.value, str) else None
                self.sql.append({**self.context(node), "call": ast.unparse(node), "queryExpression": ast.unparse(first),
                                 "literalSQL": literal, "classification": "literal" if literal is not None else "dynamic_manual_review"})
            if node.func.attr in {"_insert", "_replace", "_row"}:
                first = node.args[0]
                table = first.value if isinstance(first, ast.Constant) and isinstance(first.value, str) else None
                fields = [k.arg for k in node.keywords if k.arg]
                spread = [ast.unparse(k.value) for k in node.keywords if k.arg is None]
                entry = {**self.context(node), "operation": node.func.attr, "table": table,
                         "fields": fields, "dictionarySpreads": spread, "call": ast.unparse(node)}
                if table in self.tables:
                    t = self.tables[table]
                    entry["unknownFields"] = sorted(set(fields) - set(t["columns"]))
                    entry["actualPrimaryKey"] = t["primary_key"]["columns"]
                    entry["literalEnums"] = []
                    for kw in node.keywords:
                        column = t["columns"].get(kw.arg, {})
                        allowed = column.get("allowed_values")
                        if allowed is not None:
                            values = literal_values(kw.value)
                            entry["literalEnums"].append({"column": kw.arg, "values": values, "allowed": allowed,
                                                          "invalid": [v for v in values if v is not None and v not in allowed]})
                    entry["status"] = "column_names_valid_spreads_manual" if spread else "column_names_valid"
                    if entry["unknownFields"]:
                        entry["status"] = "unknown_column"
                else:
                    entry["status"] = "dynamic_table_manual" if table is None else "unknown_table"
                self.typed.append(entry)
        self.generic_visit(node)


def main():
    assert sha(MODEL) == MODEL_SHA
    model = json.loads(MODEL.read_text())
    active = [t for s in model["schemas"] for t in s["tables"] if t["phase"] != "models"]
    tables = {t["qualified_name"]: t for t in active}
    assert len(tables) == 94 and sum(len(t["columns"]) for t in active) == 1709
    assert all(re.fullmatch(r"(ingest|football|analytics)\.[a-z_][a-z0-9_]*", q) for q in tables)
    frozen = json.loads((BASE / "THIRD_PRECODE_CHECKSUMS.json").read_text())
    frozen_before = {name: sha(BASE / name) for name in frozen["sha256"]}
    assert frozen_before == frozen["sha256"], "A frozen148-file entry changed before this static review"
    ddl = SUPPORT[0].read_text()
    definitions = {
        f"{s}.{t}": body for s, t, body in re.findall(r'CREATE TABLE "(\w+)"\."(\w+)" \((.*?)\n\);', ddl, re.S)
    }
    schema_checks = []
    for q, t in tables.items():
        body = definitions[q]
        cols = re.findall(r'^  "([^"]+)" ', body, re.M)
        primary = re.search(r'PRIMARY KEY \((.*?)\)', body)
        pk = re.findall(r'"([^"]+)"', primary[1]) if primary else []
        assert cols == list(t["columns"]), q + " column order/set differs from012"
        assert pk == t["primary_key"]["columns"], q + " PK differs from012"
        for name, column in t["columns"].items():
            line = '"' + name + '" ' + column["type"]
            if column.get("identity"):
                line += " " + column["identity"]
            if column.get("default_sql") is not None:
                line += " DEFAULT " + column["default_sql"]
            if not column["nullable"]:
                line += " NOT NULL"
            assert "  " + line + "," in body, q + "." + name + " type/default/identity/nullability differs from012"
        assert all('"' + c["name"] + '" CHECK (' + c["sql"] + ')' in body for c in t["checks"]), q + " CHECK differs from012"
        for unique in t["unique_constraints"]:
            nulls = " NULLS NOT DISTINCT" if unique.get("nulls_not_distinct") else ""
            expected = f'CONSTRAINT "{unique["name"]}" UNIQUE{nulls} ({quoted_list(unique["columns"])})'
            assert expected in body, q + " UQ differs from012"
        for fk in t["foreign_keys"]:
            ref = fk["references"]
            assert set(fk["columns"]) <= set(t["columns"])
            assert set(ref["columns"]) <= set(tables[ref["table"]]["columns"])
            expected = f'ALTER TABLE {relation(q)} ADD CONSTRAINT "{fk["name"]}" FOREIGN KEY ({quoted_list(fk["columns"])}) REFERENCES {relation(ref["table"])} ({quoted_list(ref["columns"])}) MATCH {fk["match"]} ON UPDATE {fk["on_update"]} ON DELETE {fk["on_delete"]} NOT DEFERRABLE;'
            assert expected in ddl, q + " FK endpoints/actions/deferral differ from012"
        for index in t["indexes"]:
            keys = []
            for key in index["keys"]:
                assert key["column"] in t["columns"]
                keys.append('"' + key["column"] + '"' + (" " + key["order"] if key.get("order") else "") + (" NULLS " + key["nulls"] if key.get("nulls") else ""))
            unique = "UNIQUE " if index.get("unique") else ""
            nulls = " NULLS NOT DISTINCT" if index.get("nulls_not_distinct") else ""
            where = " WHERE " + index["where_sql"] if index.get("where_sql") else ""
            expected = f'CREATE {unique}INDEX "{index["name"]}" ON {relation(q)} USING {index["method"]} ({", ".join(keys)}){nulls}{where};'
            assert expected in ddl, q + " index definition differs from012"
        schema_checks.append({"table": q, "columns": len(cols), "primaryKey": pk, "checks": len(t["checks"]),
                              "foreignKeys": len(t["foreign_keys"]), "uniqueConstraints": len(t["unique_constraints"]),
                              "indexes": len(t["indexes"]), "status": "model_ddl_columns_types_null_defaults_identity_pk_uq_fk_checks_indexes_equal"})
    accesses, sql, typed = [], [], []
    for path in HARNESSES:
        inv = Inventory(path, tables)
        inv.visit(ast.parse(path.read_text(), filename=str(path)))
        accesses += inv.accesses
        sql += inv.sql
        typed += inv.typed
    reviewed_accesses = []
    for site in accesses:
        table = raw_row_table(site)
        review = {**site}
        if table:
            review["binding"] = table
            if site["kind"] == "string_key":
                review["status"] = "real_column" if site["key"] in tables[table]["columns"] else "nonexistent_row_key"
            else:
                review["status"] = "row_container_dynamic_key_manually_reviewed"
        elif site["reachability"] == "unreachable_pilot_scenarios":
            review["status"] = "unreachable_existing_pilot_scenario_not_a_publisher_path"
        elif Path(site["source"]).name == "fixtures.py" and site["function"] == "_replace" and site["base"] == "row":
            review["status"] = "polymorphic_row_pk_fields_from_exact_model_primary_key"
        else:
            review["status"] = "metadata_dto_container_or_tuple_index_manual_matrix"
        reviewed_accesses.append(review)
    declared_functions = set(re.findall(r'CREATE(?: OR REPLACE)? FUNCTION\s+(?:"?(\w+)"?)\.(?:"?(\w+)"?)', SUPPORT[1].read_text()))
    for site in sql:
        text = site["literalSQL"]
        if text is not None:
            refs = re.findall(r'\b(?:FROM|JOIN|INTO|UPDATE)\s+((?:ingest|football|analytics)\.[a-z_][a-z0-9_]*)', text, re.I)
            site["referencedRelations"] = sorted(set(refs))
            site["nonModelRelations"] = [q for q in refs if q not in tables]
            site["existingCurrentViewReferences"] = sorted({q for q in refs if q.endswith("_current")})
    emit("ACCESS_INVENTORY.json", sorted(accesses, key=lambda r: (r["source"], r["line"], r["expression"])))
    emit("ACCESS_REVIEW.json", sorted(reviewed_accesses, key=lambda r: (r["source"], r["line"], r["expression"])))
    emit("SQL_INVENTORY.json", sorted(sql, key=lambda r: (r["source"], r["line"])))
    emit("TYPED_WRITE_INVENTORY.json", sorted(typed, key=lambda r: (r["source"], r["line"])))
    emit("MODEL_DDL_CHECKS.json", schema_checks)
    used = sorted({r["table"] for r in typed if r["table"] in tables and r["reachability"] != "unreachable_pilot_scenarios"})
    emit("REFERENCED_TABLE_CONTRACTS.json", {q: tables[q] for q in used})
    imports = []
    services = ROOT / "dashboard/backend/services"
    names = ast.parse((BASE / "publisher_workflow.py").read_text())
    service_names = next(ast.literal_eval(n.value) for n in names.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "SERVICE_NAMES" for t in n.targets))
    exported = {ROOT / "dashboard/backend/aws-app.js", *[services / n for n in service_names]}
    for path in sorted(exported):
        if path.suffix != ".js":
            continue
        for spec in re.findall(r'(?:from\s+|import\s*\()\s*["\']([^"\']+)["\']', path.read_text()):
            if spec.startswith("."):
                target = (path.parent / spec).resolve()
                imports.append({"source": str(path.relative_to(ROOT)), "specifier": spec,
                                "target": str(target.relative_to(ROOT)), "includedInExplicitExport": target in exported})
    emit("API_EXPORT_IMPORTS.json", imports)
    assert all(r["includedInExplicitExport"] for r in imports), "Explicit API export misses a local import"
    frozen_after = {name: sha(BASE / name) for name in frozen["sha256"]}
    assert frozen_after == frozen_before
    prior_receipt = json.loads((BASE / "runs/20261105T010836726415Z-owned-pg-precode-red-third-final/result.json").read_text())
    source_hashes = {str(p.relative_to(ROOT)): sha(p) for p in [MODEL, *HARNESSES, *SUPPORT]}
    compared = {p: {"current": value, "thirdRun": prior_receipt["sourceSha256"].get(p)} for p, value in source_hashes.items()}
    emit("SOURCE_RECONCILIATION.json", compared)
    result = {
        "kind": "STATIC_SCHEMA_ACCESS_INVENTORY_NOT_E2E", "databaseStarts": 0, "httpRequests": 0, "networkCalls": 0,
        "publisherExists": PUBLISHER.exists(), "modelSha256": MODEL_SHA, "activeTables": len(tables), "activeColumns": 1709,
        "schemaChecks": {"tableDefinitions": len(definitions), "matchedColumns": 1709, "matchedPrimaryKeys": 94,
                         "matchedChecks": sum(len(t["checks"]) for t in active),
                         "matchedForeignKeys": sum(len(t["foreign_keys"]) for t in active),
                         "matchedUniqueConstraints": sum(len(t["unique_constraints"]) for t in active),
                         "matchedIndexes": sum(len(t["indexes"]) for t in active)},
        "accessSiteCount": len(accesses), "stringKeySites": sum(r["kind"] == "string_key" for r in accesses),
        "sqlExecuteSites": len(sql), "literalSQLSites": sum(r["literalSQL"] is not None for r in sql),
        "typedWriteSites": len(typed), "explicitUnknownTypedFields": [r for r in typed if r.get("unknownFields")],
        "rowDictionaryBindings": sum("binding" in r for r in reviewed_accesses),
        "nonexistentRowKeys": [r for r in reviewed_accesses if r["status"] == "nonexistent_row_key"],
        "literalEnumMismatches": [r for r in typed if any(e["invalid"] for e in r.get("literalEnums", []))],
        "manualReviewRequired": True, "frozenFilesVerifiedUnchanged": len(frozen_before),
        "sourceSha256": source_hashes,
        "changesSinceThirdRun": [p for p, values in compared.items() if values["thirdRun"] is not None and values["current"] != values["thirdRun"]],
    }
    emit("INVENTORY_RESULT.json", result)
    print(json.dumps({k: result[k] for k in ["kind", "activeTables", "activeColumns", "accessSiteCount", "sqlExecuteSites", "typedWriteSites", "frozenFilesVerifiedUnchanged", "databaseStarts", "httpRequests"]}))


if __name__ == "__main__":
    main()

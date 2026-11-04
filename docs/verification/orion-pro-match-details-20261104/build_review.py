#!/usr/bin/env python3
"""Deterministic, local-only proposal materialization and review document export.

No SQL compiler, DB connection, SDK, source payload or subprocess is used.
See VISUAL_REVIEW_PROTOCOL.md for the predeclared checks and scope.
"""
import copy
import hashlib
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASE = ROOT / "docs/architecture/orion-plan-20261104/target-schema.proposed.json"
BASE_SHA = "18da43f940870b7a3a3cb49323c847dd5e5174e5eea1f8ff0c8a159cf373cb08"
MIGRATIONS = {
    "dashboard/backend/migrations/012_orion_pro_domain.sql": "f255868599c72d69f40f575a919045325ea1093a00fe4f5a6b96eae9f2c49f65",
    "dashboard/backend/migrations/013_orion_pro_integrity.sql": "85525221cad51b32aff79a777098211b4112f9f00ea7161ac93945654eeb6968",
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()


def tables(model):
    return {t["qualified_name"]: t for s in model["schemas"] for t in s["tables"]}


def counts(items):
    return {
        "tables": len(items),
        "columns": sum(len(t["columns"]) for t in items),
        "foreignKeys": sum(len(t["foreign_keys"]) for t in items),
        "jsonbColumns": sum(c["type"].lower() == "jsonb" for t in items for c in t["columns"].values()),
        "checks": sum(len(t["checks"]) for t in items),
        "primaryKeys": sum(bool(t.get("primary_key")) for t in items),
        "uniqueConstraints": sum(len(t["unique_constraints"]) for t in items),
        "indexes": sum(len(t["indexes"]) for t in items),
    }


def scopes(model):
    ts = list(tables(model).values())
    return {
        "all": counts(ts),
        "active": counts([t for t in ts if t["phase"] != "models"]),
        "deferred": counts([t for t in ts if t["phase"] == "models"]),
        "schemas": {s["name"]: counts(s["tables"]) for s in model["schemas"]},
    }


def escape_pointer(value):
    return value.replace("~", "~0").replace("/", "~1")


def make_patch(base, spec):
    locations = {t["qualified_name"]: (si, ti) for si, s in enumerate(base["schemas"]) for ti, t in enumerate(s["tables"])}
    patch = [{"op": "test", "path": "/format_version", "value": base["format_version"]},
             {"op": "test", "path": "/schemas/1/name", "value": "football"}]
    for q, change in spec["existingTableChanges"].items():
        si, ti = locations[q]
        t = base["schemas"][si]["tables"][ti]
        path = f"/schemas/{si}/tables/{ti}"
        patch.append({"op": "test", "path": path + "/qualified_name", "value": q})
        for name, value in change["replaceColumns"].items():
            p = path + "/columns/" + escape_pointer(name)
            patch.extend([{"op": "test", "path": p, "value": t["columns"][name]}, {"op": "replace", "path": p, "value": value}])
        for name, value in change.get("replaceChecks", {}).items():
            index = next(i for i, ck in enumerate(t["checks"]) if ck["name"] == name)
            p = path + f"/checks/{index}"
            patch.extend([{"op": "test", "path": p, "value": t["checks"][index]}, {"op": "replace", "path": p, "value": value}])
        for name, value in change["addColumns"].items():
            assert name not in t["columns"], (q, name, "not an addition")
            patch.append({"op": "add", "path": path + "/columns/" + escape_pointer(name), "value": value})
        for key, model_key in [("checks", "checks"), ("foreignKeys", "foreign_keys"),
                               ("uniqueConstraints", "unique_constraints"), ("indexes", "indexes")]:
            patch.extend({"op": "add", "path": path + f"/{model_key}/-", "value": value} for value in change[key])
    for t in spec["newTypedParentChildren"]:
        patch.append({"op": "add", "path": "/schemas/1/tables/-", "value": t})
        patch.append({"op": "add", "path": "/selective_versioning/parent_version_children/-", "value": t["qualified_name"]})
    patch.extend({"op": "add", "path": "/required_cross_row_rules/-", "value": r} for r in spec["newCrossRowRules"])
    return patch


def apply_document_patch(base, patch):
    candidate = copy.deepcopy(base)
    for op in patch:
        parts = [v.replace("~1", "/").replace("~0", "~") for v in op["path"].split("/")[1:]]
        owner = candidate
        for part in parts[:-1]:
            owner = owner[int(part)] if isinstance(owner, list) else owner[part]
        key = int(parts[-1]) if isinstance(owner, list) and parts[-1] != "-" else parts[-1]
        if op["op"] == "test":
            assert owner[key] == op["value"], op["path"]
        elif isinstance(owner, list):
            if op["op"] == "replace":
                assert isinstance(key, int) and 0 <= key < len(owner), op
                owner[key] = copy.deepcopy(op["value"])
            else:
                assert op["op"] == "add" and key == "-", op
                owner.append(copy.deepcopy(op["value"]))
        else:
            assert (key in owner) == (op["op"] == "replace"), op["path"]
            owner[key] = copy.deepcopy(op["value"])
    return candidate


def check_references(candidate, spec):
    ts, errors = tables(candidate), []
    for q, t in ts.items():
        columns = t["columns"]
        constraints = [t["primary_key"]] + t["unique_constraints"] + t["foreign_keys"] + t["checks"] + t["indexes"]
        names = [c["name"] for c in constraints]
        if len(names) != len(set(names)):
            errors.append([q, "duplicate constraint/index name"])
        for c in constraints:
            if len(c["name"].encode()) > 63:
                errors.append([q, c["name"], "identifier exceeds63 bytes"])
            for column in c.get("columns", []):
                if column not in columns:
                    errors.append([q, c["name"], "missing local column", column])
            for key in c.get("keys", []):
                if "column" in key and key["column"] not in columns:
                    errors.append([q, c["name"], "missing index column", key["column"]])
        for fk in t["foreign_keys"]:
            target = ts.get(fk["references"]["table"])
            target_columns = fk["references"]["columns"]
            if target is None:
                errors.append([q, fk["name"], "missing target"])
                continue
            keys = [target["primary_key"]["columns"]] + [u["columns"] for u in target["unique_constraints"]]
            if target_columns not in keys:
                errors.append([q, fk["name"], "target is not an exact PK/UQ"])
            if len(fk["columns"]) != len(target_columns):
                errors.append([q, fk["name"], "FK arity"])
            for local, remote in zip(fk["columns"], target_columns):
                if local not in columns or remote not in target["columns"]:
                    errors.append([q, fk["name"], "missing FK column"])
                elif columns[local]["type"] != target["columns"][remote]["type"]:
                    errors.append([q, fk["name"], "FK type mismatch", local, remote])
    for q, added in [(q, c["addColumns"]) for q, c in spec["existingTableChanges"].items()] + [(t["qualified_name"], t["columns"]) for t in spec["newTypedParentChildren"]]:
        t = ts[q]
        for name, column in added.items():
            if column.get("allowed_values"):
                expected = name + " IN (" + ",".join("'" + v + "'" for v in column["allowed_values"]) + ")"
                if not any(ck["sql"] == expected for ck in t["checks"]):
                    errors.append([q, name, "missing exact enum CHECK"])
        for name in [n for n in added if n.endswith("_count")]:
            state = name.removesuffix("_count") + "_state"
            check = next(ck["sql"] for ck in t["checks"] if f"{state}='present'" in ck["sql"])
            for tag, relation in [("empty", "=0"), ("present", ">0")]:
                if f"{state}='{tag}' AND {name} IS NOT NULL AND {name}{relation}" not in check:
                    errors.append([q, name, "NULL cardinality permitted", tag])
    return errors


def column_keys(t, name):
    keys = []
    if name in t["primary_key"]["columns"]:
        keys.append("PK")
    for uq in t["unique_constraints"]:
        if name in uq["columns"]:
            keys.append("UQ " + uq["name"])
    for fk in t["foreign_keys"]:
        if name in fk["columns"]:
            keys.append("FK " + fk["references"]["table"] + "(" + ",".join(fk["references"]["columns"]) + ")")
    for ix in t["indexes"]:
        if any(k.get("column") == name for k in ix.get("keys", [])):
            keys.append(("UQ index " if ix.get("unique") else "index ") + ix["name"])
    return keys


def state_description(t, name, c):
    if c.get("allowed_values"):
        return " | ".join(c["allowed_values"]) + ("; défaut " + c["default_sql"] if "default_sql" in c else "; explicite, sans défaut")
    if name.endswith("_count"):
        return name.removesuffix("_count") + "_state : absent/null→NULL ; empty→0 ; present→>0 ; legacy unrecorded→NULL si autorisé"
    aliases = {
        "player_profile_version_id": "source_player_state", "sub_in_player_profile_version_id": "source_sub_in_player_state",
        "sub_in_player_id": "source_sub_in_player_state", "source_home_team_profile_version_id": "source_home_team_state",
        "source_away_team_profile_version_id": "source_away_team_state",
    }
    state = aliases.get(name, name + "_state")
    if state in t["columns"]:
        return state + " ; NULL SQL ne prouve ni absence ni null natif"
    if name in ("home_metric_revision_id", "away_metric_revision_id"):
        return "value_kind de la révision scalaire référencée distingue absent/null/number/string/boolean ; FK toujours requise"
    if name in ("lineup_revision_id", "source_collection_from_gen"):
        return "NULL = liaison historique non renseignée ; une observation native complète doit être liée"
    return "Clé/métadonnée structurelle obligatoire, sans état de présence natif" if not c["nullable"] else "NULL SQL ; contrat de cohorte distinct de la présence native"


def dictionary(candidate, spec, field_matrix):
    ts, rows = tables(candidate), []
    additions = [(q, c["addColumns"], "existing_table_addition") for q, c in spec["existingTableChanges"].items()]
    additions += [(t["qualified_name"], t["columns"], "new_child_column") for t in spec["newTypedParentChildren"]]
    for q, columns, change in additions:
        t = ts[q]
        for name, c in columns.items():
            token = re.compile(r"(?<![A-Za-z0-9_])" + re.escape(name) + r"(?![A-Za-z0-9_])")
            paths = sorted({f["sourcePath"] for f in field_matrix["fields"] if q + "." + name in (f["destination"] + " " + f["stateDestination"])})
            rows.append({
                "table": q, "column": name, "change": change, "sqlType": c["type"], "nullable": c["nullable"],
                "defaultSQL": c.get("default_sql"), "keys": column_keys(t, name),
                "state": state_description(t, name, c), "role": c["description"], "qualifiedSourcePaths": paths,
                "checks": [ck for ck in t["checks"] if token.search(ck["sql"])],
            })
    return rows


def md(value):
    return str(value).replace("|", " / ").replace("\n", " ")


def main():
    base_bytes = BASE.read_bytes()
    assert sha(base_bytes) == BASE_SHA, "Approved base differs; stop review export"
    for path, expected in MIGRATIONS.items():
        assert sha((ROOT / path).read_bytes()) == expected, path
    base = json.loads(base_bytes)
    spec = json.loads((HERE / "AMENDMENT_SPEC.json").read_text())
    fm = json.loads((HERE / "FIELD_MATRIX.json").read_text())
    limits = json.loads((HERE / "UNCOVERED_AND_GATES.json").read_text())
    assert spec["baseModelSha256"] == BASE_SHA == fm["baseModelSha256"]
    patch = make_patch(base, spec)
    candidate = apply_document_patch(base, patch)
    bt, ct = tables(base), tables(candidate)
    new = sorted(set(ct) - set(bt))
    modified = sorted(spec["existingTableChanges"])
    assert set(bt) <= set(ct) and len(new) == 4 and len(modified) == 7
    for s, cs in zip(base["schemas"], candidate["schemas"]):
        assert [t["qualified_name"] for t in s["tables"]] == [t["qualified_name"] for t in cs["tables"][:len(s["tables"])]]
    for q in bt:
        if q not in modified:
            assert bt[q] == ct[q], q
        else:
            expected = copy.deepcopy(bt[q])
            change = spec["existingTableChanges"][q]
            expected["columns"].update(change["replaceColumns"])
            expected["columns"].update(change["addColumns"])
            for name, value in change.get("replaceChecks", {}).items():
                index = next(i for i, ck in enumerate(expected["checks"]) if ck["name"] == name)
                expected["checks"][index] = value
            for source, target in [("checks", "checks"), ("foreignKeys", "foreign_keys"), ("uniqueConstraints", "unique_constraints"), ("indexes", "indexes")]:
                expected[target] += change[source]
            assert expected == ct[q], q
    errors = check_references(candidate, spec)
    assert not errors, errors
    rows = dictionary(candidate, spec, fm)
    assert len(rows) == len({(r["table"], r["column"]) for r in rows}) == 114
    assert all(r["sqlType"] != "jsonb" for r in rows)
    for q in new:
        t = ct[q]
        assert t["write_mode"] == "immutable_with_parent" and t["versioning"]["kind"] == "parent_version_child"
        assert "recorded_to_gen" not in t["columns"]
        parent, seen = t["versioning"]["parent"], {q}
        while parent != "ingest.match_coverage":
            assert parent in new and parent not in seen, (q, parent)
            seen.add(parent)
            parent = ct[parent]["versioning"]["parent"]
    replacements = [{"table": q, "column": name, "before": bt[q]["columns"][name], "after": value}
                    for q, c in spec["existingTableChanges"].items() for name, value in c["replaceColumns"].items()]
    assert len(replacements) == 4
    added_fks = [{"table": q, **fk} for q in ct for fk in ct[q]["foreign_keys"] if q not in bt or fk not in bt[q]["foreign_keys"]]
    added_checks = [{"table": q, **ck} for q in ct for ck in ct[q]["checks"] if q not in bt or ck["name"] not in {x["name"] for x in bt[q]["checks"]}]
    replaced_checks = [{"table": q, "name": name,
                        "before": next(x for x in bt[q]["checks"] if x["name"] == name), "after": value}
                       for q, c in spec["existingTableChanges"].items() for name, value in c.get("replaceChecks", {}).items()]
    added_uqs = [{"table": q, **uq} for q in ct for uq in ct[q]["unique_constraints"] if q not in bt or uq not in bt[q]["unique_constraints"]]
    added_indexes = [{"table": q, **ix} for q in ct for ix in ct[q]["indexes"] if q not in bt or ix not in bt[q]["indexes"]]
    before, after = scopes(base), scopes(candidate)
    delta = {"kind": "PROPOSED_DOCUMENT_DELTA_NOT_SQL", "baseModelSha256": BASE_SHA,
             "countingMethod": "All definitions in model; active=phase!=models, deferred=phase=models. FK/CHECK/UQ/index counts are named model definitions, not measured PostgreSQL objects.",
             "before": before, "after": after,
             "allDelta": {k: after["all"][k] - before["all"][k] for k in before["all"]},
             "newTables": new, "modifiedTables": modified, "retainedTables": sorted(set(bt) - set(modified)),
             "existingColumnAdditions": sum(len(c["addColumns"]) for c in spec["existingTableChanges"].values()),
             "newChildColumns": sum(len(ct[q]["columns"]) for q in new),
             "columnReplacements": replacements, "addedForeignKeys": added_fks, "addedChecks": added_checks,
             "replacedChecks": replaced_checks,
             "addedUniqueConstraints": added_uqs, "addedIndexes": added_indexes,
             "newIndependentHistoryTables": 0, "newGenericValueRegistries": 0, "newSourceBodies": 0,
             "newCrossRowRuleIds": [r["id"] for r in spec["newCrossRowRules"]]}
    assert delta["allDelta"]["tables"] == 4 and delta["allDelta"]["columns"] == 114 and delta["allDelta"]["foreignKeys"] == 16
    assert delta["allDelta"]["jsonbColumns"] == 0
    candidate_bytes = encoded(candidate)
    static = {
        "kind": "STATIC_JSONPATCH_DOCUMENT_CHECK_ONLY", "baseModelSha256": BASE_SHA,
        "baseModelStillUnchanged": True, "patchOpCount": len(patch), "testsAppliedInMemory": sum(o["op"] == "test" for o in patch),
        "jsonPatchAppliedInMemory": True, "candidateJsonSha256": sha(candidate_bytes),
        "candidateFile": "target-schema.native-details.CANDIDATE.json",
        "candidateMetadataNote": "Review materialization; base planning/status metadata is retained, not a new approval.",
        "before": before, "after": after, "allDelta": delta["allDelta"],
        "existingColumnAdditions": delta["existingColumnAdditions"], "newChildColumns": delta["newChildColumns"],
        "columnReplacementCount": len(replacements), "checkReplacementCount": len(replaced_checks), "dictionaryEntries": len(rows), "retainedTableDefinitionsUnchanged": len(delta["retainedTables"]),
        "foreignKeyAndIdentifierReferenceErrors": errors, "proposedEnumsHaveExactChecks": True,
        "proposedEmptyPresentCountsRequireNonNull": True,
        "sqlCompiled": False, "sqlExecuted": False, "databaseUsed": False, "sourceReadsPerformed": False,
        "functionalTestsExecuted": False, "approvalRequestedOrImplied": False,
        "existingHeatmapCollisionEvidenceReferenced": True, "proposedHeatmapContextPgValidated": False,
    }
    dictionary_doc = {"kind": "PROPOSED_NEW_COLUMN_DICTIONARY", "baseModelSha256": BASE_SHA, "count": len(rows), "columns": rows,
                      "columnReplacements": replacements, "sqlValidated": False}
    lines = ["# Proposed column dictionary", "", "Suggested commit: `docs: propose typed native match detail amendments with cohort proofs`.", "",
             "Generated from the in-memory base+patch candidate.114 additions (65 existing-table +49 new-child),4 replacements. No SQL validation or application. State enums and scalar CHECK expressions are in AMENDMENT_SPEC.json; seven cross-row rules remain unimplemented.", "",
             "| Table | Column | SQL type | Key / reference | Nullable | State | Role |", "|---|---|---|---|---|---|---|"]
    for r in rows:
        role = r["role"] + (" Qualified: " + "; ".join(r["qualifiedSourcePaths"]) if r["qualifiedSourcePaths"] else "")
        lines.append("| " + " | ".join(md(x) for x in [r["table"], r["column"], r["sqlType"], "; ".join(r["keys"]) or "—", "yes" if r["nullable"] else "no", r["state"], role]) + " |")
    lines += ["", "## Four replacements", "", "| Table.column | Before | Proposed |", "|---|---|---|"]
    for r in replacements:
        describe = lambda c: c["type"] + (" NULL" if c["nullable"] else " NOT NULL")
        lines.append(f"| {r['table']}.{r['column']} | {describe(r['before'])} | {describe(r['after'])} |")
    lines += ["", "Two existing raw_pitch_x/y finite CHECK definitions are replaced by explicit numeric-compatible definitions (not duplicated); see MODEL_DELTA.json.replacedChecks. Relaxing nullability does not recover previously lost source states. Widening historical doubles to numeric does not recover original decimals. Existing representations need their original adapter and independent byte/ETag compatibility evidence before later publication.", ""]
    view_tables = [{**t, "reviewChange": "new" if q in new else "modified" if q in modified else "retained"} for q, t in ct.items()]
    data = {"baseSha256": BASE_SHA, "candidateSha256": sha(candidate_bytes), "delta": delta,
            "tables": view_tables, "columns": rows, "rules": spec["newCrossRowRules"], "limits": limits}
    template = (HERE / "review_template.html").read_text()
    assert template.count("__REVIEW_DATA__") == 1
    html = template.replace("__REVIEW_DATA__", json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029"))
    outputs = {"PROPOSED_MODEL.patch.json": encoded(patch), "target-schema.native-details.CANDIDATE.json": candidate_bytes,
               "STATIC_PATCH_CHECK.json": encoded(static), "MODEL_DELTA.json": encoded(delta),
               "COLUMN_DICTIONARY.json": encoded(dictionary_doc), "COLUMN_DICTIONARY.md": "\n".join(lines).encode(),
               "NATIVE_MODEL_REVIEW.html": html.encode()}
    assert BASE.read_bytes() == base_bytes
    for path, expected in MIGRATIONS.items():
        assert sha((ROOT / path).read_bytes()) == expected, path
    for name in outputs:
        assert not (HERE / name).is_symlink(), name
    for name, value in outputs.items():
        (HERE / name).write_bytes(value)
    inputs = ["AMENDMENT_SPEC.json", "FIELD_MATRIX.json", "UNCOVERED_AND_GATES.json", "review_template.html", "build_review.py", "VISUAL_REVIEW_PROTOCOL.md"]
    receipt = {"kind": "DETERMINISTIC_LOCAL_DOCUMENT_EXPORT", "command": "python3 docs/verification/orion-pro-match-details-20261104/build_review.py",
               "inputs": {str(BASE.relative_to(ROOT)): BASE_SHA, **MIGRATIONS,
                          **{str((HERE / n).relative_to(ROOT)): sha((HERE / n).read_bytes()) for n in inputs}},
               "outputs": {name: sha(value) for name, value in outputs.items()}, "counts": delta["allDelta"],
               "staticChecks": "pass; document assertions only", "baseAndMigrationsUnchanged": True,
               "browserCheck": "separate receipt; not implied by this export", "databaseUsed": False, "sourceBodiesRead": False,
               "sqlCompiled": False, "sqlExecuted": False, "cloudUsed": False, "approvedModelChanged": False}
    (HERE / "REVIEW_EXPORT.json").write_bytes(encoded(receipt))
    print(json.dumps({"status": "static-document-checks-pass", "before": before["all"], "after": after["all"], "delta": delta["allDelta"], "candidateSha256": sha(candidate_bytes)}))


if __name__ == "__main__":
    main()

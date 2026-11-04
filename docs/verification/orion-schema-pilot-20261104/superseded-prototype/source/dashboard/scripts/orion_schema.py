"""Compile the approved relational contract into additive, versioned PostgreSQL DDL."""
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "docs/architecture/orion-plan-20261104/target-schema.proposed.json"
MODEL = json.loads(SPEC.read_text())
TABLES = {t["qualified_name"]: t for s in MODEL["schemas"] for t in s["tables"] if t["phase"] != "models"}

def ident(value):
    if not re.fullmatch(r"[a-z_][a-z0-9_]*", value) or len(value.encode()) > 63:
        raise ValueError("Invalid approved SQL identifier")
    return '"' + value + '"'

def relation(value):
    return ".".join(ident(p) for p in value.split("."))

def literal(value):
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)):
        return str(value)
    return "'" + str(value).replace("'", "''") + "'"

def cols(names):
    return ", ".join(ident(n) for n in names)

def expression(value):
    if any(c in value for c in [";", "--", "/*", "\x00"]):
        raise ValueError("Unexpected statement syntax in approved SQL expression")
    return value

def short_name(name):
    return name if len(name.encode()) <= 63 else name[:50] + "_" + hashlib.sha256(name.encode()).hexdigest()[:12]

def schema_sql():
    out = ["-- Approved plan780a113da3:152 active tables;9 model tables remain documentary.",
           "-- Additive only. Do not modify the sealed003-011 migrations or legacy sources."]
    for schema in ["ingest", "football", "analytics"]:
        out += [f"CREATE SCHEMA IF NOT EXISTS {ident(schema)};", f"REVOKE ALL ON SCHEMA {ident(schema)} FROM PUBLIC;"]
    allowed_types = {"bigint", "text", "integer", "double precision", "timestamptz", "jsonb", "boolean", "date", "smallint", "numeric", "numeric(16,6)", "text[]", "numeric(12,3)", "tsvector"}
    for name, table in TABLES.items():
        definitions = []
        for column, spec in table["columns"].items():
            if spec["type"] not in allowed_types:
                raise ValueError("Unreviewed SQL type")
            line = ident(column) + " " + spec["type"]
            if spec.get("identity"):
                if spec["identity"] != "GENERATED ALWAYS AS IDENTITY":
                    raise ValueError("Unexpected identity declaration")
                line += " GENERATED ALWAYS AS IDENTITY"
            if spec.get("default_sql"):
                line += " DEFAULT " + expression(spec["default_sql"])
            if not spec["nullable"]:
                line += " NOT NULL"
            definitions.append(line)
        pk = table["primary_key"]
        definitions.append(f"CONSTRAINT {ident(pk['name'])} PRIMARY KEY ({cols(pk['columns'])})")
        for constraint in table["unique_constraints"]:
            nulls = " NULLS NOT DISTINCT" if constraint.get("nulls_not_distinct") else ""
            definitions.append(f"CONSTRAINT {ident(constraint['name'])} UNIQUE{nulls} ({cols(constraint['columns'])})")
        for constraint in table["checks"]:
            definitions.append(f"CONSTRAINT {ident(constraint['name'])} CHECK ({expression(constraint['sql'])})")
        # Enforce the approved finite-number rule for every numeric fact, including histories.
        for column, spec in table["columns"].items():
            if spec["type"].startswith(("double", "numeric")):
                cname = short_name(name.replace(".", "_") + "_" + column + "_finite")
                definitions.append(f"CONSTRAINT {ident(cname)} CHECK ({ident(column)}::text NOT IN ('NaN','Infinity','-Infinity'))")
            if column == "quality_flags":
                cname = short_name(name.replace(".", "_") + "_quality_boolean_values")
                definitions.append(f"CONSTRAINT {ident(cname)} CHECK (NOT jsonb_path_exists({ident(column)}, '$.* ? (@.type() != \"boolean\")'))")
        out.append(f"CREATE TABLE {relation(name)} (\n  " + ",\n  ".join(definitions) + "\n);")
        out.append(f"COMMENT ON TABLE {relation(name)} IS {literal(table['description'] + ' Grain: ' + table['grain'])};")
        for column, spec in table["columns"].items():
            out.append(f"COMMENT ON COLUMN {relation(name)}.{ident(column)} IS {literal(spec['description'])};")
    for name, table in TABLES.items():
        for constraint in table["foreign_keys"]:
            target = constraint["references"]
            if target["table"] not in TABLES:
                raise ValueError("Active table depends on a deferred model")
            tail = f"MATCH {constraint.get('match','SIMPLE')} ON UPDATE {constraint.get('on_update','NO ACTION')} ON DELETE {constraint.get('on_delete','RESTRICT')}"
            tail += " DEFERRABLE INITIALLY " + ("DEFERRED" if constraint.get("initially_deferred") else "IMMEDIATE") if constraint.get("deferrable") else " NOT DEFERRABLE"
            out.append(f"ALTER TABLE {relation(name)} ADD CONSTRAINT {ident(constraint['name'])} FOREIGN KEY ({cols(constraint['columns'])}) REFERENCES {relation(target['table'])} ({cols(target['columns'])}) {tail};")
        for index in table["indexes"]:
            keys = ", ".join(ident(k["column"]) + (" " + k["order"] if index["method"] == "btree" and k.get("order") else "") for k in index["keys"])
            out.append(f"CREATE {'UNIQUE ' if index.get('unique') else ''}INDEX {ident(index['name'])} ON {relation(name)} USING {index['method']} ({keys});")
    return "\n\n".join(out) + "\n"

if __name__ == "__main__":
    approval = json.loads((ROOT / "docs/verification/orion-schema-pilot-20261104/approval.json").read_text())
    if hashlib.sha256(SPEC.read_bytes()).hexdigest() != approval["schemaSha256"]:
        raise SystemExit("Approved schema fingerprint changed; review the plan before compilation")
    path = ROOT / "dashboard/backend/migrations/012_orion_domain.sql"
    path.write_text(schema_sql())
    print(json.dumps({"file": str(path.relative_to(ROOT)), "tables": len(TABLES), "columns": sum(len(t["columns"]) for t in TABLES.values())}))

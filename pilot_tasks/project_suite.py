"""The miniquery project: a small multi-module task with a dependency graph.

Unlike the flat task suites, this is one project an agent builds as five modules
that must integrate: ``parse`` (lex and parse a query), ``match`` (evaluate a
predicate against a row), ``select`` (filter rows, depending on parse and match),
``summarize`` (aggregate a numeric field) and ``render`` (format a text table).
The dependency ``select -> {parse, match}`` and the need for the modules to share
one interface are the point: they let us measure the CTA **task wrapper** (a
precise interface contract so independently produced modules snap together) and
the **agent wrapper** (route each module to the cheapest capable model and
assemble the pieces into a working whole).

Two project specs drive the ablation. ``SPEC_WRAPPED`` gives the exact interface
contract and acceptance criteria per module (the task wrapper). ``SPEC_BARE``
gives only a loose paragraph, so models pick their own internal shapes and
cross-model assembly is not guaranteed. References are hard-checked against
canonical outputs in ``_selftest``.
"""

from __future__ import annotations

# --- Reference modules (used to generate and validate the hidden cases) ---------

_OPS = [">=", "<=", "!=", "=", ">", "<"]


def _split_and(query):
    out, in_quote, token, i = [], False, "", 0
    while i < len(query):
        if query[i] == "'":
            in_quote = not in_quote
            token += query[i]
            i += 1
        elif not in_quote and query[i:i + 5] == " AND ":
            out.append(token)
            token = ""
            i += 5
        else:
            token += query[i]
            i += 1
    out.append(token)
    return out


def _take_field_op(part):
    for i in range(len(part)):
        for op in _OPS:
            if part[i:i + len(op)] == op:
                return part[:i].strip(), op, part[i + len(op):]
    raise ValueError("no operator")


def _parse_value(tok):
    if tok.startswith("'") and tok.endswith("'") and len(tok) >= 2:
        return tok[1:-1]
    try:
        return int(tok)
    except ValueError:
        return tok


def parse(query):
    query = query.strip()
    if not query:
        return []
    preds = []
    for part in _split_and(query):
        field, op, rest = _take_field_op(part.strip())
        preds.append({"field": field, "op": op, "value": _parse_value(rest.strip())})
    return preds


def match(row, predicates):
    for p in predicates:
        f, op, v = p["field"], p["op"], p["value"]
        if f not in row:
            return False
        a = row[f]
        if op == "=":
            if a != v:
                return False
        elif op == "!=":
            if a == v:
                return False
        else:
            if type(a) is not type(v):
                return False
            if op == ">" and not a > v:
                return False
            if op == "<" and not a < v:
                return False
            if op == ">=" and not a >= v:
                return False
            if op == "<=" and not a <= v:
                return False
    return True


def select(rows, query):
    preds = parse(query)
    return [r for r in rows if match(r, preds)]


def summarize(rows, field, op):
    if op == "count":
        return float(len(rows))
    vals = [
        r[field] for r in rows
        if field in r and isinstance(r[field], (int, float)) and not isinstance(r[field], bool)
    ]
    if not vals:
        return 0.0
    if op == "sum":
        return float(sum(vals))
    if op == "min":
        return float(min(vals))
    if op == "max":
        return float(max(vals))
    if op == "avg":
        return float(sum(vals)) / len(vals)
    raise ValueError(op)


def render(rows, columns):
    widths = {c: len(c) for c in columns}
    for r in rows:
        for c in columns:
            widths[c] = max(widths[c], len(str(r.get(c, ""))))
    lines = [" | ".join(c.ljust(widths[c]) for c in columns)]
    for r in rows:
        lines.append(" | ".join(str(r.get(c, "")).ljust(widths[c]) for c in columns))
    return "\n".join(lines)


REFERENCE = {
    "parse": parse,
    "match": match,
    "select": select,
    "summarize": summarize,
    "render": render,
}
MODULE_NAMES = list(REFERENCE.keys())
DEPENDS = {"select": ["parse", "match"]}

_ROWS = [
    {"name": "Ann", "age": 30, "role": "eng"},
    {"name": "Bob", "age": 25, "role": "sales"},
    {"name": "Cy", "age": 41, "role": "eng"},
    {"name": "Dee", "age": 30, "role": "ops"},
]

_INPUTS = {
    "parse": [
        ("age >= 30",), ("name = 'Bob'",), ("age > 20 AND role = 'eng'",),
        ("city != 'New York'",), ("",), ("score <= 100",), ("x = 5 AND y = 6 AND z = 7",),
    ],
    "match": [
        ({"age": 30}, [{"field": "age", "op": ">=", "value": 30}]),
        ({"age": 29}, [{"field": "age", "op": ">=", "value": 30}]),
        ({"name": "Bob"}, [{"field": "name", "op": "=", "value": "Bob"}]),
        ({"age": 30}, [{"field": "role", "op": "=", "value": "x"}]),
        ({"age": 30}, [{"field": "age", "op": ">", "value": "x"}]),
        ({"age": 30, "role": "eng"},
         [{"field": "age", "op": ">=", "value": 30}, {"field": "role", "op": "=", "value": "eng"}]),
    ],
    "select": [
        (_ROWS, "age >= 30 AND role = 'eng'"), (_ROWS, "role = 'ops'"),
        (_ROWS, "age > 100"), (_ROWS, "age != 30"), (_ROWS, ""),
    ],
    "summarize": [
        (_ROWS, "age", "count"), (_ROWS, "age", "sum"), (_ROWS, "age", "min"),
        (_ROWS, "age", "max"), (_ROWS, "age", "avg"), ([], "age", "avg"),
        (_ROWS, "role", "sum"),
    ],
    "render": [
        ([{"name": "Ann", "age": 30}], ["name", "age"]),
        ([], ["a", "bb"]),
        (_ROWS, ["name", "role"]),
        ([{"name": "Ann", "age": 30}, {"name": "Cy", "age": 41}], ["name", "age"]),
    ],
}

CASES = {
    name: [(args, REFERENCE[name](*args)) for args in inputs]
    for name, inputs in _INPUTS.items()
}


def score_namespace(ns: dict, name: str) -> float:
    """Fraction of a module's hidden cases passed by ns[name] (0 on any error)."""
    fn = ns.get(name)
    if not callable(fn):
        return 0.0
    passed = 0
    for args, expected in CASES[name]:
        try:
            if fn(*args) == expected:
                passed += 1
        except Exception:
            pass
    return passed / len(CASES[name])


def validate() -> dict[str, float]:
    ns = dict(REFERENCE)
    return {name: score_namespace(ns, name) for name in MODULE_NAMES}


SPEC_BARE = """\
Build a tiny in-memory query toolkit as five Python functions in one module.

- parse(query): turn a query string into a list of conditions.
- match(row, predicates): does a row (a dict) satisfy the conditions?
- select(rows, query): return the rows matching the query (use parse and match).
- summarize(rows, field, op): aggregate a field with op in count/sum/min/max/avg.
- render(rows, columns): format the rows as a simple text table.

Queries look like "age >= 30 AND role = 'eng'". Make them work together.

Return each function in its own block:
### MODULE: <name>
CONFIDENCE: <0..1>
```python
<the function>
```"""

SPEC_WRAPPED = """\
Build the miniquery toolkit as five Python functions in ONE shared module so they
integrate. Honour these exact interface contracts (other modules and other agents
depend on them) and the acceptance criteria.

def parse(query: str) -> list[dict]:
    '''Parse a query into a list of {"field": str, "op": str, "value": int|str}.
    Grammar: CONDITION (" AND " CONDITION)*, CONDITION is FIELD OP VALUE.
    OP is one of =, !=, >, <, >=, <= (match >= and <= before > and <).
    VALUE: a single-quoted string 'like this' (may contain spaces; strip the
    quotes) OR an integer (optionally negative) OR a bareword string.
    The empty/whitespace query returns []. e.g. parse("age > 20 AND role = 'eng'")
    -> [{"field":"age","op":">","value":20},{"field":"role","op":"=","value":"eng"}].'''

def match(row: dict, predicates: list[dict]) -> bool:
    '''True iff row satisfies every predicate. If a predicate's field is absent
    from row, return False. For = and != compare directly. For >, <, >=, <= return
    False when the row value and the predicate value are different types, else
    apply the comparison.'''

def select(rows: list[dict], query: str) -> list[dict]:
    '''Return [r for r in rows if match(r, parse(query))]. Call parse and match by
    name (they are defined in the same module).'''

def summarize(rows: list[dict], field: str, op: str) -> float:
    '''op in {count,sum,min,max,avg}. count -> float(len(rows)). The others use the
    numeric values of field over rows that have it (skip missing/non-numeric); an
    empty selection returns 0.0; avg is the mean. Always return a float.'''

def render(rows: list[dict], columns: list[str]) -> str:
    '''Return a text table. First line is the column names; then one line per row.
    Cells are str(value) (missing -> ''), left-justified (ljust) to the widest
    cell in that column including the header, columns joined by " | ". Rows joined
    by "\\n". With no rows, return just the header line.'''

Self-check parse("name = 'New York City'"), select over rows for
"age >= 30 AND role = 'eng'", summarize([], "age", "avg") -> 0.0, and render of a
one-row table so the header pads to the widest cell.

Each function MUST be self-contained: define any helper INSIDE the function body.
The only cross-module names you may call are parse, match, select, summarize and
render themselves (select calls parse and match). This lets each module be graded
and assembled independently. Return each module in its own block:
### MODULE: <name>
CONFIDENCE: <0..1>
```python
<the function>
```"""


def _selftest() -> None:
    assert parse("age > 20 AND role = 'eng'") == [
        {"field": "age", "op": ">", "value": 20},
        {"field": "role", "op": "=", "value": "eng"}]
    assert [r["name"] for r in select(_ROWS, "age >= 30 AND role = 'eng'")] == ["Ann", "Cy"]
    assert summarize(_ROWS, "age", "avg") == 31.5
    assert summarize([], "age", "avg") == 0.0
    assert render([{"name": "Ann", "age": 30}], ["name", "age"]) == "name | age\nAnn  | 30 "
    assert all(v == 1.0 for v in validate().values())


if __name__ == "__main__":
    _selftest()
    print(f"OK: miniquery project, {len(MODULE_NAMES)} modules, references validated")

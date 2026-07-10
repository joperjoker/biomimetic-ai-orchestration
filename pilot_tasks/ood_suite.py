"""Out-of-distribution overconfidence tasks for the two-sided calibration curve.

The live pilot on the standard suite found the Claude models uniformly
*underconfident* (they under-promise and over-deliver), so the measured
calibration curve only ever populated its upper-left, underconfident arm. A
two-sided curve needs the overconfident arm too: cases where a model's stated
confidence exceeds its realised pass rate. That arm shows up on tasks a model
believes it knows cold but slips on, so these eight are classic, genuinely
solvable algorithms whose difficulty is entirely in edge cases a confident model
tends to skip: 32-bit clamping (my_atoi, reverse_integer), Unix path
canonicalisation (simplify_path), version-revision comparison (compare_version),
zero-traps in run-length decoding (decode_ways), bijective base-26
(title_to_number), the look-and-say recurrence (count_and_say), and subtractive
Roman numerals (int_to_roman).

The two-sided curve is measured on ``BARE_SPECS``: a bare signature with one line
and no edge cases named, so a model prices its confidence on the happy path and
the hidden edge cases expose the overconfidence. ``SPECS`` (the task-wrapped
envelope that names the edge cases) is included for the same wrapper-ablation the
expert suite runs, and is expected to move the same model toward calibration.

Every reference is a standard algorithm, hard-checked against canonical outputs in
``_selftest`` (and in ``tests/test_ood_suite.py``), so the generated hidden cases
cannot silently encode a reference bug.
"""

from __future__ import annotations

# --- Reference solutions (used only to generate and validate hidden cases) ------

_INT_MIN, _INT_MAX = -(2**31), 2**31 - 1


def _my_atoi(s):
    i, n = 0, len(s)
    while i < n and s[i] == " ":
        i += 1
    sign = 1
    if i < n and s[i] in "+-":
        sign = -1 if s[i] == "-" else 1
        i += 1
    num = 0
    while i < n and s[i].isdigit():
        num = num * 10 + int(s[i])
        i += 1
    num *= sign
    if num < _INT_MIN:
        return _INT_MIN
    if num > _INT_MAX:
        return _INT_MAX
    return num


def _reverse_integer(x):
    sign = -1 if x < 0 else 1
    r = int(str(abs(x))[::-1]) * sign
    return 0 if r < _INT_MIN or r > _INT_MAX else r


def _simplify_path(path):
    stack = []
    for part in path.split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            if stack:
                stack.pop()
        else:
            stack.append(part)
    return "/" + "/".join(stack)


def _compare_version(v1, v2):
    a = [int(x) for x in v1.split(".")]
    b = [int(x) for x in v2.split(".")]
    for i in range(max(len(a), len(b))):
        x = a[i] if i < len(a) else 0
        y = b[i] if i < len(b) else 0
        if x < y:
            return -1
        if x > y:
            return 1
    return 0


def _decode_ways(s):
    if not s or s[0] == "0":
        return 0
    n = len(s)
    prev2, prev1 = 1, 1
    for i in range(2, n + 1):
        cur = 0
        if s[i - 1] != "0":
            cur += prev1
        if 10 <= int(s[i - 2 : i]) <= 26:
            cur += prev2
        prev2, prev1 = prev1, cur
    return prev1


def _title_to_number(s):
    r = 0
    for c in s:
        r = r * 26 + (ord(c) - ord("A") + 1)
    return r


def _count_and_say(n):
    s = "1"
    for _ in range(n - 1):
        res = []
        i = 0
        while i < len(s):
            j = i
            while j < len(s) and s[j] == s[i]:
                j += 1
            res.append(str(j - i))
            res.append(s[i])
            i = j
        s = "".join(res)
    return s


def _int_to_roman(n):
    vals = [
        (1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"),
        (90, "XC"), (50, "L"), (40, "XL"), (10, "X"), (9, "IX"),
        (5, "V"), (4, "IV"), (1, "I"),
    ]
    res = []
    for v, sym in vals:
        while n >= v:
            res.append(sym)
            n -= v
    return "".join(res)


REFERENCE = {
    "my_atoi": _my_atoi,
    "reverse_integer": _reverse_integer,
    "simplify_path": _simplify_path,
    "compare_version": _compare_version,
    "decode_ways": _decode_ways,
    "title_to_number": _title_to_number,
    "count_and_say": _count_and_say,
    "int_to_roman": _int_to_roman,
}

# --- Inputs for the hidden cases (edge-dense; expected outputs are generated) ----

_INPUTS = {
    "my_atoi": [
        ("42",), ("   -42",), ("4193 with words",), ("words and 987",),
        ("-91283472332",), ("+1",), ("  +0 123",), ("3.14",), ("+-12",),
        ("2147483648",), ("-2147483648",), ("  0000000000012345678",),
        ("",), ("   ",), ("-000000000000001",), ("2147483646",), ("  -0012a42",),
        ("9223372036854775808",),
    ],
    "reverse_integer": [
        (123,), (-123,), (120,), (0,), (1534236469,), (-2147483648,),
        (1463847412,), (-1463847412,), (100,), (7,), (-10,), (2147483647,),
        (1000000003,), (-100,), (901,), (2147447412,),
    ],
    "simplify_path": [
        ("/home/",), ("/../",), ("/home//foo/",), ("/a/./b/../../c/",),
        ("/a/../../b/../c//.//",), ("/...",), ("/.hidden",), ("/",),
        ("/a//b////c/d//././/..",), ("/..hidden/",), ("/abc/...",),
        ("/a/b/c/../..",), ("/./.",), ("/foo/../foo/bar",),
    ],
    "compare_version": [
        ("1.01", "1.001"), ("1.0", "1.0.0"), ("0.1", "1.1"), ("1.2", "1.10"),
        ("1", "1.0"), ("7.5.2.4", "7.5.3"), ("1.0.0", "1"), ("0.0.0", "0"),
        ("1.01.1", "1.1.1"), ("10", "2"), ("1.1", "1.1.0.0.0"), ("2.0", "10.0"),
    ],
    "decode_ways": [
        ("12",), ("226",), ("0",), ("06",), ("10",), ("100",), ("27",),
        ("101",), ("110",), ("11106",), ("2101",), ("1",), ("2611055971756562",),
        ("301",), ("10011",), ("2020",),
    ],
    "title_to_number": [
        ("A",), ("AB",), ("ZY",), ("AA",), ("Z",), ("AZ",), ("BA",),
        ("ZZ",), ("AAA",), ("FXSHRXW",), ("BZ",), ("YZ",), ("AAB",), ("CFB",),
    ],
    "count_and_say": [
        (1,), (2,), (3,), (4,), (5,), (6,), (7,), (8,), (9,), (10,),
    ],
    "int_to_roman": [
        (3,), (4,), (9,), (58,), (1994,), (3999,), (40,), (3888,), (1,),
        (14,), (49,), (90,), (400,), (944,), (2021,), (1000,),
    ],
}

CASES = {
    name: [(args, REFERENCE[name](*args)) for args in inputs]
    for name, inputs in _INPUTS.items()
}

# --- Task-wrapped envelope (SPECS) and bare prompt (BARE_SPECS) ------------------
# The two-sided calibration curve is measured on BARE_SPECS; SPECS is the wrapped
# envelope for the same wrapper ablation the expert suite runs.

SPECS = {
    "my_atoi": '''\
def my_atoi(s: str) -> int:
    """Convert a string to a 32-bit signed integer (the classic atoi rules).
    Acceptance criteria the hidden tests check:
    - skip leading spaces, then an optional single '+'/'-', then digits; stop at
      the first non-digit (so '4193 with words' -> 4193, 'words 9' -> 0).
    - clamp to [-2**31, 2**31-1]: '2147483648' -> 2147483647, overflow negatives
      to -2147483648.
    - '3.14' -> 3; '+-12' -> 0; empty or all-spaces -> 0.
    Self-check: trace '2147483648', '  +0 123', '-91283472332'."""''',
    "reverse_integer": '''\
def reverse_integer(x: int) -> int:
    """Reverse the digits of a signed 32-bit integer.
    Acceptance criteria:
    - keep the sign; drop leading zeros of the result (120 -> 21).
    - if the reversed value falls outside [-2**31, 2**31-1], return 0.
    Self-check: 1534236469 -> 0 (overflow), -123 -> -321, 120 -> 21."""''',
    "simplify_path": '''\
def simplify_path(path: str) -> str:
    """Canonicalise a Unix-style absolute path.
    Acceptance criteria:
    - collapse repeated slashes; '.' is the current dir; '..' pops one level
      (and is a no-op at the root).
    - a name of three or more dots ('...') is an ordinary name, not a parent.
    - the result starts with a single '/' and has no trailing slash (root -> '/').
    Self-check: '/a/./b/../../c/' -> '/c'; '/...' -> '/...'; '/../' -> '/'."""''',
    "compare_version": '''\
def compare_version(version1: str, version2: str) -> int:
    """Compare two dotted version strings; return -1, 0, or 1.
    Acceptance criteria:
    - compare revision by revision as integers, so '1.01' == '1.001' and
      leading zeros do not matter.
    - a missing trailing revision counts as 0, so '1.0' == '1' == '1.0.0'.
    Self-check: '1.2' vs '1.10' -> -1; '1.0.0' vs '1' -> 0."""''',
    "decode_ways": '''\
def decode_ways(s: str) -> int:
    """Count the ways to decode a digit string where '1'..'26' map to 'A'..'Z'.
    Acceptance criteria:
    - '0' is not a letter: it can only appear as part of '10' or '20'; any other
      '0' makes that segment undecodable (so '100' -> 0, '06' -> 0).
    - a leading '0' or empty string -> 0. Use dynamic programming.
    Self-check: '226' -> 3; '10' -> 1; '27' -> 1; '2101' -> 1."""''',
    "title_to_number": '''\
def title_to_number(column: str) -> int:
    """Convert an Excel column title ('A','B',...,'Z','AA',...) to its number.
    Acceptance criteria:
    - this is bijective base 26 with no zero digit: 'A' -> 1, 'Z' -> 26,
      'AA' -> 27, 'AZ' -> 52, 'BA' -> 53.
    Self-check: 'ZY' -> 701; 'AA' -> 27; 'FXSHRXW' -> 2147483647."""''',
    "count_and_say": '''\
def count_and_say(n: int) -> str:
    """Return the n-th term (1-indexed) of the look-and-say sequence.
    Acceptance criteria:
    - term 1 is '1'; each next term reads the previous as runs of (count, digit)
      left to right, so '1' -> '11' -> '21' -> '1211' -> '111221'.
    Self-check: n=5 -> '111221'; n=6 -> '312211'."""''',
    "int_to_roman": '''\
def int_to_roman(n: int) -> str:
    """Convert an integer in 1..3999 to a Roman numeral.
    Acceptance criteria:
    - use subtractive forms IV(4), IX(9), XL(40), XC(90), CD(400), CM(900);
      never four of the same symbol in a row.
    Self-check: 4 -> 'IV'; 58 -> 'LVIII'; 1994 -> 'MCMXCIV'; 3999 -> 'MMMCMXCIX'."""''',
}

BARE_SPECS = {
    "my_atoi": "def my_atoi(s: str) -> int:  # convert a string to a 32-bit signed "
    "integer, e.g. '42' -> 42.",
    "reverse_integer": "def reverse_integer(x: int) -> int:  # reverse the digits of a "
    "signed integer, e.g. 123 -> 321.",
    "simplify_path": "def simplify_path(path: str) -> str:  # canonicalise a Unix "
    "absolute path, e.g. '/a/./b/' -> '/a/b'.",
    "compare_version": "def compare_version(version1: str, version2: str) -> int:  # -1, "
    "0 or 1 comparing two dotted versions.",
    "decode_ways": "def decode_ways(s: str) -> int:  # number of ways to decode digits "
    "where 1..26 map to A..Z, e.g. '12' -> 2.",
    "title_to_number": "def title_to_number(column: str) -> int:  # Excel column title to "
    "its number, e.g. 'AB' -> 28.",
    "count_and_say": "def count_and_say(n: int) -> str:  # the n-th look-and-say term, "
    "e.g. n=4 -> '1211'.",
    "int_to_roman": "def int_to_roman(n: int) -> str:  # integer (1..3999) to a Roman "
    "numeral, e.g. 58 -> 'LVIII'.",
}

TASK_NAMES = list(REFERENCE.keys())


def score(name, func) -> float:
    """Fraction of hidden cases the function passes (0 on any exception)."""
    cases = CASES[name]
    passed = 0
    for args, expected in cases:
        try:
            if func(*args) == expected:
                passed += 1
        except Exception:
            pass
    return passed / len(cases)


def validate() -> dict[str, float]:
    """Every reference solution must pass all of its own hidden cases."""
    return {name: score(name, REFERENCE[name]) for name in TASK_NAMES}


def _selftest() -> None:
    """Hard canonical checks so a buggy reference cannot ship silently."""
    assert _my_atoi("2147483648") == 2147483647
    assert _my_atoi("-91283472332") == -2147483648
    assert _my_atoi("4193 with words") == 4193
    assert _my_atoi("words and 987") == 0
    assert _reverse_integer(1534236469) == 0
    assert _reverse_integer(120) == 21
    assert _reverse_integer(-123) == -321
    assert _simplify_path("/a/./b/../../c/") == "/c"
    assert _simplify_path("/...") == "/..."
    assert _simplify_path("/../") == "/"
    assert _compare_version("1.01", "1.001") == 0
    assert _compare_version("1.2", "1.10") == -1
    assert _compare_version("1.0.0", "1") == 0
    assert _decode_ways("226") == 3
    assert _decode_ways("100") == 0
    assert _decode_ways("2101") == 1
    assert _decode_ways("06") == 0
    assert _title_to_number("ZY") == 701
    assert _title_to_number("FXSHRXW") == 2147483647
    assert _count_and_say(5) == "111221"
    assert _count_and_say(6) == "312211"
    assert _int_to_roman(1994) == "MCMXCIV"
    assert _int_to_roman(3999) == "MMMCMXCIX"
    assert _int_to_roman(58) == "LVIII"
    assert all(v == 1.0 for v in validate().values())


if __name__ == "__main__":
    _selftest()
    print(f"OK: {len(TASK_NAMES)} OOD tasks, all references validated")

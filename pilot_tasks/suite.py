"""The live-pilot task suite: coding micro-tasks with validated hidden tests.

Each task has a spec the agent sees (signature and behaviour, a couple of visible
examples), a reference solution used only to validate the hidden tests, and a set
of hidden cases including edge cases the spec does not spell out. The agent states
a confidence (its probability of passing all hidden cases) before solving, so we
measure real self-report against real outcome. The reference is never shown to the
agent; ``validate()`` checks that every reference passes its own hidden cases.
"""

from __future__ import annotations

# --- Reference solutions (used only to validate the hidden cases) ---------------


def _run_length_encode(s):
    if not s:
        return ""
    out = []
    prev, count = s[0], 1
    for ch in s[1:]:
        if ch == prev:
            count += 1
        else:
            out.append(f"{prev}{count}")
            prev, count = ch, 1
    out.append(f"{prev}{count}")
    return "".join(out)


def _roman_to_int(s):
    vals = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    total = 0
    for i, ch in enumerate(s):
        v = vals[ch]
        if i + 1 < len(s) and vals[s[i + 1]] > v:
            total -= v
        else:
            total += v
    return total


def _is_balanced(s):
    pairs = {")": "(", "]": "[", "}": "{"}
    stack = []
    for ch in s:
        if ch in "([{":
            stack.append(ch)
        elif ch in ")]}":
            if not stack or stack.pop() != pairs[ch]:
                return False
    return not stack


def _merge_intervals(intervals):
    if not intervals:
        return []
    ordered = sorted((list(iv) for iv in intervals), key=lambda x: x[0])
    merged = [ordered[0][:]]
    for a, b in ordered[1:]:
        if a <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    return merged


def _expand_ranges(s):
    out = []
    for part in s.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-")
            out.extend(range(int(a), int(b) + 1))
        else:
            out.append(int(part))
    return out


def _chunk(lst, n):
    return [lst[i : i + n] for i in range(0, len(lst), n)]


def _deep_get(d, path, default=None):
    cur = d
    for key in path.split("."):
        if isinstance(cur, dict) and key in cur:
            cur = cur[key]
        else:
            return default
    return cur


def _caesar(s, k):
    out = []
    for ch in s:
        if "a" <= ch <= "z":
            out.append(chr((ord(ch) - 97 + k) % 26 + 97))
        elif "A" <= ch <= "Z":
            out.append(chr((ord(ch) - 65 + k) % 26 + 65))
        else:
            out.append(ch)
    return "".join(out)


REFERENCE = {
    "run_length_encode": _run_length_encode,
    "roman_to_int": _roman_to_int,
    "is_balanced": _is_balanced,
    "merge_intervals": _merge_intervals,
    "expand_ranges": _expand_ranges,
    "chunk": _chunk,
    "deep_get": _deep_get,
    "caesar": _caesar,
}

# --- Hidden cases: (args_tuple, expected). Edge cases included deliberately. -----

CASES = {
    "run_length_encode": [
        (("aaabbc",), "a3b2c1"),
        (("",), ""),
        (("x",), "x1"),
        (("aabbaa",), "a2b2a2"),
        (("zzzzz",), "z5"),
    ],
    "roman_to_int": [
        (("III",), 3),
        (("IV",), 4),
        (("IX",), 9),
        (("LVIII",), 58),
        (("MCMXCIV",), 1994),
        (("XL",), 40),
    ],
    "is_balanced": [
        (("()[]{}",), True),
        (("(]",), False),
        (("([)]",), False),
        (("{[]}",), True),
        (("",), True),
        (("(((",), False),
    ],
    "merge_intervals": [
        (([[1, 3], [2, 6], [8, 10], [15, 18]],), [[1, 6], [8, 10], [15, 18]]),
        (([[1, 4], [4, 5]],), [[1, 5]]),
        (([[3, 5], [1, 2]],), [[1, 2], [3, 5]]),
        (([],), []),
        (([[1, 4], [2, 3]],), [[1, 4]]),
    ],
    "expand_ranges": [
        (("1-3,5,7-9",), [1, 2, 3, 5, 7, 8, 9]),
        (("5",), [5]),
        (("1-1",), [1]),
        (("1, 3-4",), [1, 3, 4]),
        (("10-12",), [10, 11, 12]),
    ],
    "chunk": [
        (([1, 2, 3, 4, 5], 2), [[1, 2], [3, 4], [5]]),
        (([1], 3), [[1]]),
        (([], 3), []),
        (([1, 2, 3, 4], 2), [[1, 2], [3, 4]]),
    ],
    "deep_get": [
        (({"a": {"b": 1}}, "a.b"), 1),
        (({"a": {"b": 1}}, "a.c"), None),
        (({"a": {"b": 1}}, "a.b.c"), None),
        (({"x": {"y": {"z": 7}}}, "x.y.z"), 7),
        (({}, "a"), None),
    ],
    "caesar": [
        (("abc", 1), "bcd"),
        (("xyz", 3), "abc"),
        (("AbZ", 2), "CdB"),
        (("a!b", 1), "b!c"),
        (("Hello, World!", 13), "Uryyb, Jbeyq!"),
    ],
}

# --- Specs the agent sees (behaviour + a couple of visible examples) -------------

SPECS = {
    "run_length_encode": (
        "def run_length_encode(s: str) -> str:\n"
        "    '''Run-length encode a string as character then count, e.g.\n"
        "    'aaabbc' -> 'a3b2c1'. Handle the empty string and single characters.'''"
    ),
    "roman_to_int": (
        "def roman_to_int(s: str) -> int:\n"
        "    '''Convert an uppercase Roman numeral to an integer, e.g. 'LVIII' -> 58.\n"
        "    Handle subtractive forms like IV and IX.'''"
    ),
    "is_balanced": (
        "def is_balanced(s: str) -> bool:\n"
        "    '''Return whether the brackets (), [], {} in s are correctly matched and\n"
        "    nested, e.g. '{[]}' -> True. Other characters are ignored.'''"
    ),
    "merge_intervals": (
        "def merge_intervals(intervals: list[list[int]]) -> list[list[int]]:\n"
        "    '''Merge overlapping intervals and return them sorted by start, e.g.\n"
        "    [[1,3],[2,6]] -> [[1,6]]. The input may be unsorted.'''"
    ),
    "expand_ranges": (
        "def expand_ranges(s: str) -> list[int]:\n"
        "    '''Expand a comma-separated list of numbers and a-b ranges into a list,\n"
        "    e.g. '1-3,5' -> [1,2,3,5].'''"
    ),
    "chunk": (
        "def chunk(lst: list, n: int) -> list[list]:\n"
        "    '''Split lst into consecutive chunks of size n (the last may be shorter),\n"
        "    e.g. chunk([1,2,3,4,5], 2) -> [[1,2],[3,4],[5]].'''"
    ),
    "deep_get": (
        "def deep_get(d: dict, path: str, default=None):\n"
        "    '''Look up a dotted path in a nested dict, e.g. deep_get({'a':{'b':1}}, 'a.b')\n"
        "    -> 1. Return default if any key along the path is missing.'''"
    ),
    "caesar": (
        "def caesar(s: str, k: int) -> str:\n"
        "    '''Caesar-shift letters in s by k, wrapping within the alphabet and\n"
        "    preserving case; leave non-letters unchanged. e.g. caesar('abc',1)->'bcd'.'''"
    ),
}

# --- Harder tasks: edge-case-heavy, to elicit a spread of outcomes -------------


def _int_to_roman(n):
    table = [
        (1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"), (90, "XC"),
        (50, "L"), (40, "XL"), (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I"),
    ]
    out = []
    for v, sym in table:
        while n >= v:
            out.append(sym)
            n -= v
    return "".join(out)


def _valid_ipv4(s):
    parts = s.split(".")
    if len(parts) != 4:
        return False
    for p in parts:
        if not p.isdigit():
            return False
        if len(p) > 1 and p[0] == "0":
            return False
        if not 0 <= int(p) <= 255:
            return False
    return True


def _next_bigger(n):
    digits = list(str(n))
    i = len(digits) - 2
    while i >= 0 and digits[i] >= digits[i + 1]:
        i -= 1
    if i < 0:
        return -1
    j = len(digits) - 1
    while digits[j] <= digits[i]:
        j -= 1
    digits[i], digits[j] = digits[j], digits[i]
    digits[i + 1:] = reversed(digits[i + 1:])
    return int("".join(digits))


def _spreadsheet_column(name):
    result = 0
    for ch in name:
        result = result * 26 + (ord(ch) - ord("A") + 1)
    return result


def _format_duration(seconds):
    if seconds == 0:
        return "now"
    units = [("year", 31536000), ("day", 86400), ("hour", 3600), ("minute", 60), ("second", 1)]
    parts = []
    for name, size in units:
        q, seconds = divmod(seconds, size)
        if q:
            parts.append(f"{q} {name}" + ("s" if q > 1 else ""))
    if len(parts) == 1:
        return parts[0]
    return ", ".join(parts[:-1]) + " and " + parts[-1]


REFERENCE.update({
    "int_to_roman": _int_to_roman,
    "valid_ipv4": _valid_ipv4,
    "next_bigger": _next_bigger,
    "spreadsheet_column": _spreadsheet_column,
    "format_duration": _format_duration,
})

CASES.update({
    "int_to_roman": [
        ((3,), "III"), ((4,), "IV"), ((9,), "IX"), ((40,), "XL"), ((90,), "XC"),
        ((400,), "CD"), ((900,), "CM"), ((1994,), "MCMXCIV"), ((3888,), "MMMDCCCLXXXVIII"),
    ],
    "valid_ipv4": [
        (("1.2.3.4",), True), (("0.0.0.0",), True), (("255.255.255.255",), True),
        (("01.2.3.4",), False), (("256.1.1.1",), False), (("1.2.3",), False),
        (("1.2.3.4.5",), False), (("1.2.3.04",), False), (("a.b.c.d",), False),
    ],
    "next_bigger": [
        ((12,), 21), ((513,), 531), ((2017,), 2071), ((9,), -1), ((111,), -1),
        ((531,), -1), ((144,), 414), ((12345,), 12354),
    ],
    "spreadsheet_column": [
        (("A",), 1), (("Z",), 26), (("AA",), 27), (("AZ",), 52), (("BA",), 53),
        (("ZZ",), 702), (("AAA",), 703),
    ],
    "format_duration": [
        ((0,), "now"), ((1,), "1 second"), ((62,), "1 minute and 2 seconds"),
        ((120,), "2 minutes"), ((3600,), "1 hour"),
        ((3662,), "1 hour, 1 minute and 2 seconds"),
        ((86400,), "1 day"), ((31536000,), "1 year"),
    ],
})

SPECS.update({
    "int_to_roman": (
        "def int_to_roman(n: int) -> str:\n"
        "    '''Convert an integer (1..3999) to an uppercase Roman numeral, e.g.\n"
        "    1994 -> 'MCMXCIV'. Handle subtractive forms (4->IV, 9->IX, 40, 90, 400, 900).'''"
    ),
    "valid_ipv4": (
        "def valid_ipv4(s: str) -> bool:\n"
        "    '''Return whether s is a valid IPv4 address: four decimal octets 0..255\n"
        "    separated by dots, with no leading zeros (so '01' is invalid).'''"
    ),
    "next_bigger": (
        "def next_bigger(n: int) -> int:\n"
        "    '''Return the smallest integer greater than n using exactly the same digits,\n"
        "    or -1 if none exists. e.g. next_bigger(513) -> 531, next_bigger(531) -> -1.'''"
    ),
    "spreadsheet_column": (
        "def spreadsheet_column(name: str) -> int:\n"
        "    '''Convert a spreadsheet column name to its 1-based number, e.g.\n"
        "    'A' -> 1, 'Z' -> 26, 'AA' -> 27.'''"
    ),
    "format_duration": (
        "def format_duration(seconds: int) -> str:\n"
        "    '''Format a duration in seconds as a human string using years (365 days),\n"
        "    days, hours, minutes and seconds; omit zero units; use singular/plural; join\n"
        "    with commas and ' and ' before the last; 0 -> 'now'. e.g. 62 -> '1 minute and\n"
        "    2 seconds'.'''"
    ),
})

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


if __name__ == "__main__":
    print(validate())

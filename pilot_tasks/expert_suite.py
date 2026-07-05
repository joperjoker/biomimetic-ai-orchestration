"""Expert-tier live-pilot tasks: hard enough to separate model capability.

The standard suite (`suite.py`) is solved to the ceiling by every current Claude
model, so it cannot show a capability ladder. These eight tasks are classic but
trap-dense (repeating-decimal detection, English number formatting, full text
justification, a parenthesised calculator, big-integer string multiply, the
minimum window substring, word break, wildcard matching). Weaker models slip on
their edge cases while stronger ones do not, which is exactly the spread the
capability-ladder and wrapper-ablation study needs.

Two spec variants per task drive the wrapper ablation:

- ``SPECS`` is the **task-wrapped** envelope: the full CTA scent, with the
  acceptance criteria and the edge cases named, plus a self-check contract. This
  is what a task advertises under CTA.
- ``BARE_SPECS`` is the unwrapped prompt: signature and one line, no acceptance
  criteria. The gap between the two measures what the task wrapper buys.

Every reference is a standard algorithm, hard-checked against canonical outputs
in ``_selftest`` (and in ``tests/test_expert_suite.py``), so the generated hidden
cases cannot silently encode a reference bug.
"""

from __future__ import annotations

# --- Reference solutions (used only to generate and validate hidden cases) ------


def _fraction_to_decimal(numerator, denominator):
    if numerator == 0:
        return "0"
    sign = "-" if (numerator < 0) != (denominator < 0) else ""
    n, d = abs(numerator), abs(denominator)
    integer, rem = divmod(n, d)
    if rem == 0:
        return sign + str(integer)
    frac = []
    seen = {}
    while rem != 0:
        if rem in seen:
            i = seen[rem]
            frac.insert(i, "(")
            frac.append(")")
            break
        seen[rem] = len(frac)
        rem *= 10
        frac.append(str(rem // d))
        rem %= d
    return sign + str(integer) + "." + "".join(frac)


def _int_to_words(n):
    if n == 0:
        return "Zero"
    below20 = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven",
               "Eight", "Nine", "Ten", "Eleven", "Twelve", "Thirteen",
               "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen",
               "Nineteen"]
    tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy",
            "Eighty", "Ninety"]

    def three(x):
        r = []
        if x >= 100:
            r.append(below20[x // 100])
            r.append("Hundred")
            x %= 100
        if x >= 20:
            r.append(tens[x // 10])
            x %= 10
        if x > 0:
            r.append(below20[x])
        return r

    groups = ["", "Thousand", "Million", "Billion"]
    chunks = []
    i = 0
    while n > 0:
        if n % 1000 != 0:
            chunks.append((three(n % 1000), groups[i]))
        n //= 1000
        i += 1
    words = []
    for w, g in reversed(chunks):
        words.extend(w)
        if g:
            words.append(g)
    return " ".join(words)


def _full_justify(words, max_width):
    res = []
    line = []
    length = 0
    for w in words:
        if length + len(line) + len(w) > max_width:
            spaces = max_width - length
            if len(line) == 1:
                res.append(line[0] + " " * spaces)
            else:
                gaps = len(line) - 1
                base, extra = divmod(spaces, gaps)
                s = ""
                for i, tok in enumerate(line[:-1]):
                    s += tok + " " * (base + (1 if i < extra else 0))
                s += line[-1]
                res.append(s)
            line = []
            length = 0
        line.append(w)
        length += len(w)
    last = " ".join(line)
    last += " " * (max_width - len(last))
    res.append(last)
    return res


def _calculate3(s):
    def helper(it):
        stack = []
        num = 0
        op = "+"
        while True:
            ch = next(it, None)
            if ch == " ":
                continue
            if ch is not None and ch.isdigit():
                num = num * 10 + int(ch)
            elif ch == "(":
                num = helper(it)
            else:  # operator, ')', or end of stream
                if op == "+":
                    stack.append(num)
                elif op == "-":
                    stack.append(-num)
                elif op == "*":
                    stack.append(stack.pop() * num)
                elif op == "/":
                    prev = stack.pop()
                    stack.append(int(prev / num))
                num = 0
                if ch is None or ch == ")":
                    return sum(stack)
                op = ch
    return helper(iter(s))


def _multiply_strings(num1, num2):
    if num1 == "0" or num2 == "0":
        return "0"
    m, n = len(num1), len(num2)
    res = [0] * (m + n)
    for i in range(m - 1, -1, -1):
        for j in range(n - 1, -1, -1):
            mul = (ord(num1[i]) - 48) * (ord(num2[j]) - 48)
            p1, p2 = i + j, i + j + 1
            total = mul + res[p2]
            res[p2] = total % 10
            res[p1] += total // 10
    out = "".join(map(str, res)).lstrip("0")
    return out or "0"


def _min_window(s, t):
    if not t or not s:
        return ""
    from collections import Counter
    need = Counter(t)
    missing = len(t)
    left = start = end = 0
    for right, ch in enumerate(s, 1):
        if need[ch] > 0:
            missing -= 1
        need[ch] -= 1
        if missing == 0:
            while left < right and need[s[left]] < 0:
                need[s[left]] += 1
                left += 1
            if end == 0 or right - left < end - start:
                start, end = left, right
    return s[start:end]


def _word_break(s, words):
    wset = set(words)
    n = len(s)
    dp = [False] * (n + 1)
    dp[0] = True
    for i in range(1, n + 1):
        for j in range(i):
            if dp[j] and s[j:i] in wset:
                dp[i] = True
                break
    return dp[n]


def _is_match(s, p):
    m, n = len(s), len(p)
    dp = [[False] * (n + 1) for _ in range(m + 1)]
    dp[0][0] = True
    for j in range(1, n + 1):
        if p[j - 1] == "*":
            dp[0][j] = dp[0][j - 1]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if p[j - 1] == "*":
                dp[i][j] = dp[i - 1][j] or dp[i][j - 1]
            elif p[j - 1] == "?" or p[j - 1] == s[i - 1]:
                dp[i][j] = dp[i - 1][j - 1]
    return dp[m][n]


REFERENCE = {
    "fraction_to_decimal": _fraction_to_decimal,
    "int_to_words": _int_to_words,
    "full_justify": _full_justify,
    "calculate3": _calculate3,
    "multiply_strings": _multiply_strings,
    "min_window": _min_window,
    "word_break": _word_break,
    "is_match": _is_match,
}

# --- Inputs for the hidden cases (edge-dense; expected outputs are generated) ----

_INPUTS = {
    "fraction_to_decimal": [
        (1, 2), (2, 1), (2, 3), (4, 333), (-50, 8), (1, 6), (0, 5), (1, 333),
        (7, -12), (-1, -3), (50, 8), (1, 7), (22, 7), (100, 1), (-2, 3),
        (1, 17), (6, 4), (-7, 1), (1, 90), (10, 3),
    ],
    "int_to_words": [
        (0,), (1,), (13,), (20,), (21,), (100,), (101,), (123,), (1000,),
        (1000000,), (1234567,), (12345,), (1000000000,), (2147483647,), (999,),
        (1000001,), (500,), (70,), (305,), (4000000,), (1000010,),
    ],
    "full_justify": [
        (["This", "is", "an", "example", "of", "text", "justification."], 16),
        (["What", "must", "be", "acknowledgment", "shall", "be"], 16),
        (["a"], 1),
        (["Science", "is", "what", "we", "understand", "well", "enough",
          "to", "explain", "to", "a", "computer."], 20),
        (["Listen", "to", "many,", "speak", "to", "a", "few."], 6),
        (["word"], 8),
        (["a", "b", "c", "d", "e"], 3),
    ],
    "calculate3": [
        ("2*(5+5*2)/3+(6/2+8)",), ("(2+6*3+5-(3*14/7+2)*5)+3",), ("3+2*2",),
        (" 6-4/2 ",), ("2*3+4",), ("100",), ("1-1+1",), ("14-3/2",),
        ("(1+(4+5+2)-3)+(6+8)",), ("2*(3+(4*5))",), ("0",), ("10/3",),
        ("1000000",), ("(7)-(3)*(2)",),
    ],
    "multiply_strings": [
        ("0", "52"), ("123", "456"), ("2", "3"), ("999", "999"), ("0", "0"),
        ("1", "0"), ("100", "100"), ("9", "99"), ("123456789", "987654321"),
        ("50", "20"), ("11", "11"), ("6", "501"),
    ],
    "min_window": [
        ("ADOBECODEBANC", "ABC"), ("a", "a"), ("a", "aa"), ("aa", "aa"),
        ("cabwefgewcwaefgcf", "cae"), ("bba", "ab"), ("ab", "b"),
        ("abc", "ac"), ("aaaaaaaaaaaabbbbbcdd", "abcdd"), ("this", ""),
        ("", "a"), ("xyz", "abc"),
    ],
    "word_break": [
        ("leetcode", ["leet", "code"]),
        ("catsandog", ["cats", "dog", "sand", "and", "cat"]),
        ("applepenapple", ["apple", "pen"]),
        ("aaaaaaa", ["aaaa", "aaa"]),
        ("cars", ["car", "ca", "rs"]),
        ("", ["a"]),
        ("ab", ["a"]),
        ("goalspecial", ["go", "goal", "goals", "special"]),
        ("aaaaaaaaab", ["a"]),
    ],
    "is_match": [
        ("aa", "a"), ("aa", "*"), ("cb", "?a"), ("adceb", "*a*b"),
        ("acdcb", "a*c?b"), ("", "*"), ("", ""), ("", "?"), ("abc", "abc"),
        ("abc", "a?c"), ("mississippi", "m??*ss*?i*pi"), ("aab", "c*a*b"),
        ("ho", "**ho"), ("xaylmz", "x?y*z"),
    ],
}

CASES = {
    name: [(args, REFERENCE[name](*args)) for args in inputs]
    for name, inputs in _INPUTS.items()
}

# --- Task-wrapped envelope (SPECS) and bare prompt (BARE_SPECS) ------------------

SPECS = {
    "fraction_to_decimal": '''\
def fraction_to_decimal(numerator: int, denominator: int) -> str:
    """Return the fraction numerator/denominator as a decimal string.
    Acceptance criteria the hidden tests check:
    - numerator 0 returns '0' (no sign, no point).
    - the sign is negative iff exactly one operand is negative.
    - an exact quotient has no decimal point (2/1 -> '2').
    - a repeating decimal wraps the repeating block in parentheses at its
      first occurrence: 2/3 -> '0.(6)', 1/6 -> '0.1(6)', 4/333 -> '0.(012)'.
    Self-check before answering: trace -50/8, 1/6, 4/333, 0/5, 7/-12."""''',
    "int_to_words": '''\
def int_to_words(n: int) -> str:
    """Convert a non-negative integer (0..2**31-1) to English words with words
    space-separated and each word capitalised.
    Acceptance criteria:
    - 0 -> 'Zero'; 123 -> 'One Hundred Twenty Three'.
    - group by Thousand/Million/Billion; omit any all-zero group and never emit
      a trailing or double space; 1000000 -> 'One Million' (no 'Thousand').
    - no hyphens (45 -> 'Forty Five'), no 'and'.
    Self-check: trace 0, 100, 1000000, 1234567, 1000010."""''',
    "full_justify": '''\
def full_justify(words: list[str], max_width: int) -> list[str]:
    """Greedily pack words into lines of exactly max_width chars, full-justified.
    Acceptance criteria:
    - extra spaces go left-to-right so earlier gaps are >= later gaps.
    - a line with a single word is left-justified (padded on the right).
    - the LAST line is left-justified: single spaces between words, padded on
      the right to max_width.
    Self-check: trace the classic 16-width example and a single-word line."""''',
    "calculate3": '''\
def calculate3(s: str) -> int:
    """Evaluate an arithmetic expression of non-negative integers with + - * /,
    parentheses and spaces, honouring precedence and parentheses.
    Acceptance criteria:
    - '*' and '/' bind tighter than '+'/'-'; parentheses override.
    - division truncates toward zero (so -3/2 -> -1, not -2).
    - ignore all spaces; the result may be negative.
    Self-check: '2*(5+5*2)/3+(6/2+8)' -> 21, '(2+6*3+5-(3*14/7+2)*5)+3' -> -12."""''',
    "multiply_strings": '''\
def multiply_strings(num1: str, num2: str) -> str:
    """Multiply two non-negative integers given as strings, returning the product
    as a string, WITHOUT using int()/float()/big-int conversion of the whole.
    Acceptance criteria:
    - if either input is '0' the result is '0' (no leading zeros ever).
    - handles inputs far beyond 64-bit.
    Self-check: '0'*'52' -> '0', '123'*'456' -> '56088', '999'*'999' -> '998001'."""''',
    "min_window": '''\
def min_window(s: str, t: str) -> str:
    """Return the shortest substring of s containing every character of t
    including multiplicity; '' if none exists.
    Acceptance criteria:
    - counts multiplicity: min_window('a','aa') -> '' (needs two a's).
    - t may be empty -> '' ; either string may be empty.
    - if several windows tie on length, return the earliest.
    Self-check: 'ADOBECODEBANC','ABC' -> 'BANC'; 'a','a' -> 'a'."""''',
    "word_break": '''\
def word_break(s: str, words: list[str]) -> bool:
    """Return whether s can be segmented into a space-separated sequence of one
    or more words from the list (each word reusable).
    Acceptance criteria:
    - empty s -> True (zero words). Use dynamic programming, not naive recursion
      (inputs like 'aaaa...ab' with words ['a'] must not blow up).
    Self-check: 'leetcode',['leet','code'] -> True;
    'catsandog',['cats','dog','sand','and','cat'] -> False."""''',
    "is_match": '''\
def is_match(s: str, p: str) -> bool:
    """Wildcard match of pattern p against the whole string s, where '?' matches
    any single character and '*' matches any sequence including empty.
    Acceptance criteria:
    - '*' can match the empty string; the match must cover all of s and p.
    - '' matches '*' and '' but not '?'.
    Self-check: ('aa','*')->True, ('cb','?a')->False, ('adceb','*a*b')->True,
    ('acdcb','a*c?b')->False."""''',
}

BARE_SPECS = {
    "fraction_to_decimal": "def fraction_to_decimal(numerator: int, denominator: int) "
    "-> str:  # numerator/denominator as a decimal string, e.g. 1/2 -> '0.5'.",
    "int_to_words": "def int_to_words(n: int) -> str:  # a non-negative integer in "
    "English words, e.g. 123 -> 'One Hundred Twenty Three'.",
    "full_justify": "def full_justify(words: list[str], max_width: int) -> list[str]:  "
    "# pack words into fully-justified lines of width max_width.",
    "calculate3": "def calculate3(s: str) -> int:  # evaluate an arithmetic string "
    "with + - * / and parentheses, e.g. '2*(5+5)' -> 20.",
    "multiply_strings": "def multiply_strings(num1: str, num2: str) -> str:  # product "
    "of two non-negative integer strings, e.g. '123'*'456' -> '56088'.",
    "min_window": "def min_window(s: str, t: str) -> str:  # shortest substring of s "
    "containing all characters of t, or ''.",
    "word_break": "def word_break(s: str, words: list[str]) -> bool:  # can s be "
    "segmented into words from the list?",
    "is_match": "def is_match(s: str, p: str) -> bool:  # wildcard match where '?' is "
    "any char and '*' is any sequence.",
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
    assert _fraction_to_decimal(1, 6) == "0.1(6)"
    assert _fraction_to_decimal(4, 333) == "0.(012)"
    assert _fraction_to_decimal(-50, 8) == "-6.25"
    assert _int_to_words(1234567) == (
        "One Million Two Hundred Thirty Four Thousand Five Hundred Sixty Seven")
    assert _int_to_words(1000000) == "One Million"
    assert _full_justify(
        ["This", "is", "an", "example", "of", "text", "justification."], 16
    ) == ["This    is    an", "example  of text", "justification.  "]
    assert _calculate3("(2+6*3+5-(3*14/7+2)*5)+3") == -12
    assert _multiply_strings("999", "999") == "998001"
    assert _min_window("ADOBECODEBANC", "ABC") == "BANC"
    assert _word_break("catsandog", ["cats", "dog", "sand", "and", "cat"]) is False
    assert _is_match("acdcb", "a*c?b") is False
    assert all(v == 1.0 for v in validate().values())


if __name__ == "__main__":
    _selftest()
    print(f"OK: {len(TASK_NAMES)} expert tasks, all references validated")

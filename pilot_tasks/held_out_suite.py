"""Held-out expert tier: a second, independent 8-task suite for generalisation.

The capability ladder and wrapper ablation were measured on ``expert_suite.py``.
To show the task-wrapper lift is a property of the mechanism and not an artefact
of one hand-picked task set, this is a structurally independent tier of eight
different trap-dense classics (matrix spiral order, longest valid parentheses,
interval merging, maximum subarray, product-except-self, longest substring
without repeats, search in a rotated array, coin change), disjoint from both
``expert_suite`` and ``ood_suite``. Same two-condition design (bare vs the
task-wrapped envelope) and the same one-shot, no-tools protocol, so the lift here
is directly comparable to the primary tier.

Every reference is a standard algorithm, hard-checked against canonical outputs in
``_selftest`` (and ``tests/test_held_out_suite.py``), so the generated hidden
cases cannot silently encode a reference bug.
"""

from __future__ import annotations


def _spiral_order(matrix):
    if not matrix or not matrix[0]:
        return []
    res = []
    top, bottom = 0, len(matrix) - 1
    left, right = 0, len(matrix[0]) - 1
    while top <= bottom and left <= right:
        for c in range(left, right + 1):
            res.append(matrix[top][c])
        top += 1
        for r in range(top, bottom + 1):
            res.append(matrix[r][right])
        right -= 1
        if top <= bottom:
            for c in range(right, left - 1, -1):
                res.append(matrix[bottom][c])
            bottom -= 1
        if left <= right:
            for r in range(bottom, top - 1, -1):
                res.append(matrix[r][left])
            left += 1
    return res


def _longest_valid_parentheses(s):
    stack = [-1]
    best = 0
    for i, ch in enumerate(s):
        if ch == "(":
            stack.append(i)
        else:
            stack.pop()
            if not stack:
                stack.append(i)
            else:
                best = max(best, i - stack[-1])
    return best


def _merge_intervals(intervals):
    if not intervals:
        return []
    ordered = sorted(intervals, key=lambda x: x[0])
    res = [list(ordered[0])]
    for a, b in ordered[1:]:
        if a <= res[-1][1]:
            res[-1][1] = max(res[-1][1], b)
        else:
            res.append([a, b])
    return res


def _max_subarray(nums):
    best = cur = nums[0]
    for x in nums[1:]:
        cur = max(x, cur + x)
        best = max(best, cur)
    return best


def _product_except_self(nums):
    n = len(nums)
    res = [1] * n
    pre = 1
    for i in range(n):
        res[i] = pre
        pre *= nums[i]
    suf = 1
    for i in range(n - 1, -1, -1):
        res[i] *= suf
        suf *= nums[i]
    return res


def _length_of_longest_substring(s):
    last = {}
    start = 0
    best = 0
    for i, ch in enumerate(s):
        if ch in last and last[ch] >= start:
            start = last[ch] + 1
        last[ch] = i
        best = max(best, i - start + 1)
    return best


def _search_rotated(nums, target):
    lo, hi = 0, len(nums) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if nums[mid] == target:
            return mid
        if nums[lo] <= nums[mid]:
            if nums[lo] <= target < nums[mid]:
                hi = mid - 1
            else:
                lo = mid + 1
        else:
            if nums[mid] < target <= nums[hi]:
                lo = mid + 1
            else:
                hi = mid - 1
    return -1


def _coin_change(coins, amount):
    inf = float("inf")
    dp = [0] + [inf] * amount
    for a in range(1, amount + 1):
        for c in coins:
            if c <= a and dp[a - c] + 1 < dp[a]:
                dp[a] = dp[a - c] + 1
    return dp[amount] if dp[amount] != inf else -1


REFERENCE = {
    "spiral_order": _spiral_order,
    "longest_valid_parentheses": _longest_valid_parentheses,
    "merge_intervals": _merge_intervals,
    "max_subarray": _max_subarray,
    "product_except_self": _product_except_self,
    "length_of_longest_substring": _length_of_longest_substring,
    "search_rotated": _search_rotated,
    "coin_change": _coin_change,
}

_INPUTS = {
    "spiral_order": [
        ([[1, 2, 3], [4, 5, 6], [7, 8, 9]],),
        ([[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12]],),
        ([[1]],),
        ([[1, 2, 3]],),
        ([[1], [2], [3]],),
        ([],),
        ([[1, 2], [3, 4]],),
        ([[7]],),
    ],
    "longest_valid_parentheses": [
        ("(()",), (")()())",), ("",), ("()(()",), ("()(())",), ("))))",),
        ("()()",), ("(()())",), (")(",), ("(((",),
    ],
    "merge_intervals": [
        ([[1, 3], [2, 6], [8, 10], [15, 18]],),
        ([[1, 4], [4, 5]],),
        ([[1, 4], [2, 3]],),
        ([[1, 4], [0, 4]],),
        ([[1, 4], [5, 6]],),
        ([[2, 3], [4, 5], [6, 7], [8, 9], [1, 10]],),
        ([[1, 4]],),
        ([],),
    ],
    "max_subarray": [
        ([-2, 1, -3, 4, -1, 2, 1, -5, 4],), ([1],), ([5, 4, -1, 7, 8],),
        ([-1, -2, -3],), ([-5],), ([0, 0, 0],), ([8, -19, 5, -4, 20],),
        ([1, 2, 3, 4],),
    ],
    "product_except_self": [
        ([1, 2, 3, 4],), ([-1, 1, 0, -3, 3],), ([2, 3],), ([0, 0],),
        ([1, 0],), ([5],), ([1, 1, 1, 1],), ([-1, -1, -1],),
    ],
    "length_of_longest_substring": [
        ("abcabcbb",), ("bbbbb",), ("pwwkew",), ("",), (" ",), ("au",),
        ("dvdf",), ("abba",), ("tmmzuxt",), ("anviaj",),
    ],
    "search_rotated": [
        ([4, 5, 6, 7, 0, 1, 2], 0), ([4, 5, 6, 7, 0, 1, 2], 3),
        ([1], 0), ([1], 1), ([5, 1, 3], 5), ([4, 5, 6, 7, 0, 1, 2], 5),
        ([1, 3], 3), ([3, 1], 1), ([5, 6, 7, 0, 1, 2, 4], 4),
    ],
    "coin_change": [
        ([1, 2, 5], 11), ([2], 3), ([1], 0), ([1, 2, 5], 0),
        ([2, 5, 10, 1], 27), ([5], 5), ([3, 7], 5), ([1, 5, 10, 25], 63),
        ([2, 4], 7),
    ],
}

CASES = {
    name: [(args, REFERENCE[name](*args)) for args in inputs]
    for name, inputs in _INPUTS.items()
}

SPECS = {
    "spiral_order": '''\
def spiral_order(matrix: list[list[int]]) -> list[int]:
    """Return all elements of the matrix in clockwise spiral order, starting at
    the top-left, going right then down then left then up, spiralling inward.
    Acceptance criteria:
    - an empty matrix or empty rows return [].
    - handles non-square shapes and single rows/columns without repeating cells.
    Self-check: [[1,2,3],[4,5,6],[7,8,9]] -> [1,2,3,6,9,8,7,4,5]."""''',
    "longest_valid_parentheses": '''\
def longest_valid_parentheses(s: str) -> int:
    """Length of the longest substring of well-formed parentheses.
    Acceptance criteria:
    - only contiguous, properly matched runs count: '(()' -> 2, ')()())' -> 4.
    - empty string -> 0. Use a stack or DP, not brute force.
    Self-check: '()(())' -> 6; '))))' -> 0."""''',
    "merge_intervals": '''\
def merge_intervals(intervals: list[list[int]]) -> list[list[int]]:
    """Merge all overlapping intervals; return them sorted by start as [s, e] pairs.
    Acceptance criteria:
    - intervals that merely touch (end == next start) merge: [1,4],[4,5] -> [1,5].
    - the input is not pre-sorted; empty input -> [].
    Self-check: [[1,3],[2,6],[8,10],[15,18]] -> [[1,6],[8,10],[15,18]]."""''',
    "max_subarray": '''\
def max_subarray(nums: list[int]) -> int:
    """Return the largest sum of any non-empty contiguous subarray (Kadane).
    Acceptance criteria:
    - the subarray must be non-empty, so an all-negative array returns its
      largest single element, not 0.
    Self-check: [-2,1,-3,4,-1,2,1,-5,4] -> 6; [-1,-2,-3] -> -1."""''',
    "product_except_self": '''\
def product_except_self(nums: list[int]) -> list[int]:
    """Return an array where output[i] is the product of all elements except
    nums[i], WITHOUT using division.
    Acceptance criteria:
    - handle zeros correctly (one zero zeroes every other position but not its
      own; two zeros zero everything).
    Self-check: [1,2,3,4] -> [24,12,8,6]; [-1,1,0,-3,3] -> [0,0,9,0,0]."""''',
    "length_of_longest_substring": '''\
def length_of_longest_substring(s: str) -> int:
    """Length of the longest substring with no repeating characters.
    Acceptance criteria:
    - use a sliding window; when a repeat is found, move the window start to just
      after the previous occurrence (do not reset to 0).
    - empty string -> 0; a single space -> 1.
    Self-check: 'abcabcbb' -> 3; 'abba' -> 2; 'pwwkew' -> 3."""''',
    "search_rotated": '''\
def search_rotated(nums: list[int], target: int) -> int:
    """Search a rotated ascending array of distinct ints; return the index of
    target or -1. Must run in O(log n) (modified binary search).
    Acceptance criteria:
    - one half of any mid split is always sorted; decide which half to keep by
      comparing target against the sorted half's bounds.
    Self-check: ([4,5,6,7,0,1,2],0) -> 4; ([4,5,6,7,0,1,2],3) -> -1."""''',
    "coin_change": '''\
def coin_change(coins: list[int], amount: int) -> int:
    """Fewest coins summing to amount, or -1 if impossible; each coin reusable.
    Acceptance criteria:
    - amount 0 -> 0; if no combination reaches amount, return -1.
    - use dynamic programming over amounts, not greedy (greedy is wrong for
      arbitrary denominations).
    Self-check: ([1,2,5],11) -> 3; ([2],3) -> -1; ([1,2,5],0) -> 0."""''',
}

BARE_SPECS = {
    "spiral_order": "def spiral_order(matrix: list[list[int]]) -> list[int]:  # matrix "
    "elements in clockwise spiral order.",
    "longest_valid_parentheses": "def longest_valid_parentheses(s: str) -> int:  # length "
    "of the longest well-formed parentheses substring.",
    "merge_intervals": "def merge_intervals(intervals: list[list[int]]) -> list[list[int]]:"
    "  # merge overlapping intervals.",
    "max_subarray": "def max_subarray(nums: list[int]) -> int:  # largest sum of a "
    "contiguous non-empty subarray.",
    "product_except_self": "def product_except_self(nums: list[int]) -> list[int]:  # "
    "product of all elements except self, no division.",
    "length_of_longest_substring": "def length_of_longest_substring(s: str) -> int:  # "
    "length of the longest substring without repeating characters.",
    "search_rotated": "def search_rotated(nums: list[int], target: int) -> int:  # index "
    "of target in a rotated sorted array, or -1.",
    "coin_change": "def coin_change(coins: list[int], amount: int) -> int:  # fewest "
    "coins summing to amount, or -1.",
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
    assert _spiral_order([[1, 2, 3], [4, 5, 6], [7, 8, 9]]) == [1, 2, 3, 6, 9, 8, 7, 4, 5]
    assert _spiral_order([[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12]]) == [
        1, 2, 3, 4, 8, 12, 11, 10, 9, 5, 6, 7]
    assert _spiral_order([]) == []
    assert _longest_valid_parentheses("(()") == 2
    assert _longest_valid_parentheses(")()())") == 4
    assert _longest_valid_parentheses("()(())") == 6
    assert _merge_intervals([[1, 3], [2, 6], [8, 10], [15, 18]]) == [[1, 6], [8, 10], [15, 18]]
    assert _merge_intervals([[1, 4], [4, 5]]) == [[1, 5]]
    assert _max_subarray([-2, 1, -3, 4, -1, 2, 1, -5, 4]) == 6
    assert _max_subarray([-1, -2, -3]) == -1
    assert _product_except_self([1, 2, 3, 4]) == [24, 12, 8, 6]
    assert _product_except_self([-1, 1, 0, -3, 3]) == [0, 0, 9, 0, 0]
    assert _length_of_longest_substring("abcabcbb") == 3
    assert _length_of_longest_substring("abba") == 2
    assert _search_rotated([4, 5, 6, 7, 0, 1, 2], 0) == 4
    assert _search_rotated([4, 5, 6, 7, 0, 1, 2], 3) == -1
    assert _coin_change([1, 2, 5], 11) == 3
    assert _coin_change([2], 3) == -1
    assert _coin_change([1, 2, 5], 0) == 0
    assert all(v == 1.0 for v in validate().values())


if __name__ == "__main__":
    _selftest()
    print(f"OK: {len(TASK_NAMES)} held-out tasks, all references validated")

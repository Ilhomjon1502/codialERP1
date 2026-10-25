"""Ovozdan kelgan nomni bazadagi yozuvga moslash (kategoriya, g'azna, kreditor, xodim…): aniq → ichida bor → so'zlar → o'xshashlik.
Bitta mos topilsa — o'sha; bir nechtasi yoki hech biri bo'lmasa — tanlash uchun variantlar."""

import difflib
import re

APOSTROPHES = "ʻʼ’‘`´'"
MAX_OPTIONS = 6


def norm(s):
    s = str(s or "").lower().strip()
    for ch in APOSTROPHES:
        s = s.replace(ch, "'")
    s = s.replace("g'aznasi", "").replace("g'azna", "")
    return re.sub(r"\s+", " ", re.sub(r"[^\w' ]", " ", s)).strip()


def _tokens(s):
    return [t for t in norm(s).replace("'", "").split() if t]


def find(name, candidates):
    """candidates: [(obj, label)]. Qaytaradi: (obj | None, [(obj, label)] — tanlash uchun variantlar)."""
    candidates = list(candidates)
    n = norm(name)
    if not n:
        return None, candidates[:MAX_OPTIONS]
    exact = [c for c in candidates if norm(c[1]) == n]
    if len(exact) == 1:
        return exact[0][0], []
    inside = [c for c in candidates if n in norm(c[1]) or (norm(c[1]) and norm(c[1]) in n)]
    if len(inside) == 1:
        return inside[0][0], []
    toks = _tokens(name)
    by_tokens = [c for c in candidates if toks and all(any(lt.startswith(t[:4]) or t.startswith(lt[:4]) for lt in _tokens(c[1])) for t in toks)]
    if len(by_tokens) == 1:
        return by_tokens[0][0], []
    pool = inside or by_tokens or candidates
    scored = sorted(pool, key=lambda c: difflib.SequenceMatcher(None, n, norm(c[1])).ratio(), reverse=True)
    if not inside and not by_tokens and scored:
        best = difflib.SequenceMatcher(None, n, norm(scored[0][1])).ratio()
        second = difflib.SequenceMatcher(None, n, norm(scored[1][1])).ratio() if len(scored) > 1 else 0
        if best >= 0.8 and best - second >= 0.1:
            return scored[0][0], []
    return None, scored[:MAX_OPTIONS]

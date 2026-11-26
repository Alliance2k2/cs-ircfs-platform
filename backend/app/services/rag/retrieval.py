"""BM25 baseline and reciprocal rank fusion; no compulsory model dependency."""
import math
import re
from collections import Counter

STOP = set("how do does i the is a an can what for to and of in with my are on it use me please".split())
# Common question scaffolding must not create evidence by itself (for example,
# 'should receive' matching a privacy passage for a fertilizer-dose question).
STOP.update("should which about that there they their would could will you your we our whom when where why receive provide get give".split())


def tokenize(text):
    return [word for word in re.findall(r"[^\W_]{3,}", text.casefold()) if word not in STOP]


def bm25(question, sources, top_k=3, minimum=0.0):
    if not 1 <= top_k <= 20 or minimum < 0:
        raise ValueError("Invalid retrieval parameters")
    terms = set(tokenize(question))
    counts = [Counter(tokenize(source["title"] + " " + source["title"] + " " + source["text"])) for source in sources]
    average = sum(sum(row.values()) for row in counts) / max(1, len(counts)) or 1
    frequency = Counter(word for row in counts for word in row)
    ranked = []
    for source, row in zip(sources, counts):
        score = 0.0
        for word in terms & row.keys():
            idf = math.log(1 + (len(counts) - frequency[word] + .5) / (frequency[word] + .5))
            score += idf * row[word] * 2.2 / (row[word] + 1.2 * (.25 + .75 * sum(row.values()) / average))
        if score > minimum:
            ranked.append((score, source))
    return [dict(source, retrieval_score=round(score, 6)) for score, source in sorted(ranked, key=lambda item: (-item[0], item[1]["id"]))[:top_k]]


def fuse(rankings, top_k=3, constant=60):
    if constant < 1 or not 1 <= top_k <= 20:
        raise ValueError("Invalid fusion parameters")
    scores, sources = Counter(), {}
    for ranking in rankings:
        seen = set()
        for rank, source in enumerate(ranking, 1):
            if source["id"] in seen:
                continue
            seen.add(source["id"])
            sources[source["id"]] = source
            scores[source["id"]] += 1 / (constant + rank)
    return [dict(sources[key], retrieval_score=round(score, 6)) for key, score in sorted(scores.items(), key=lambda item: (-item[1], item[0]))[:top_k]]


def context(sources, max_chars=16000):
    """Keep full selected chunks only; never silently truncate supporting evidence."""
    selected = []
    remaining = max_chars
    for source in sources:
        cost = len(source["title"]) + len(source["text"]) + 200
        if cost <= remaining:
            selected.append(source)
            remaining -= cost
    return selected

"""Derive open/run actions. Typed entries first, then markdown-inline syntax.
Literal !, backslash, ~ never create actions."""
import re

_LINK_RE = re.compile(r"\[([^\]]*)\]\((https?://[^)\s]+)\)")
_BARE_RE = re.compile(r"https?://[^\s)>\]`'\"]+")
_INLINE_CMD_RE = re.compile(r"`([^`\n]+)`")
_FENCED_RE = re.compile(r"```(?:sh|bash|shell)?[ \t]*\n(.*?)```", re.DOTALL)

def _strip_trailing_punct(url: str) -> str:
    return url.rstrip(".,;:!?)]}'\"")

def _extract_links(text: str) -> list[dict]:
    acts, seen = [], set()
    for m in _LINK_RE.finditer(text):
        url = _strip_trailing_punct(m.group(2))
        if url not in seen:
            seen.add(url)
            acts.append({"kind": "open", "target": url,
                         "label": m.group(1) or url})
    for m in _BARE_RE.finditer(text):
        url = _strip_trailing_punct(m.group(0))
        if url not in seen:
            seen.add(url)
            acts.append({"kind": "open", "target": url, "label": url})
    return acts

def _extract_inline_cmds(text: str) -> list[dict]:
    no_fence = _FENCED_RE.sub("", text)
    return [{"kind": "run", "target": m.group(1).strip(), "label": m.group(1).strip()}
            for m in _INLINE_CMD_RE.finditer(no_fence) if m.group(1).strip()]

def _extract_fenced(text: str) -> list[dict]:
    acts = []
    for m in _FENCED_RE.finditer(text):
        for line in m.group(1).splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                acts.append({"kind": "run", "target": line, "label": line})
    return acts

def extract_actions(entry: dict) -> list[dict]:
    etype, body, title = entry.get("type", "note"), entry.get("body", ""), entry.get("title", "")
    if etype == "url":
        url = body.strip().splitlines()[0].strip() if body.strip() else ""
        base = [{"kind": "open", "target": url, "label": title or url}] if url else []
        return base + [a for a in _extract_links(body) if a["target"] != url]
    if etype == "cmd":
        lines = [ln.strip() for ln in body.splitlines() if ln.strip()]
        return [{"kind": "run", "target": ln, "label": title or ln} for ln in lines]
    return _extract_links(body) + _extract_inline_cmds(body) + _extract_fenced(body)

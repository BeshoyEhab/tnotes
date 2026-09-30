"""Typed Entry model. Sole schema definition; JSONL lines stay compatible."""
import re
from dataclasses import dataclass, field

SCHEMA_VERSION = 2
_ID_RE = re.compile(r"[0-9a-f]{6}")

class EntryNotFound(Exception):
    pass

class AmbiguousPrefix(KeyError):
    pass

class NoActionError(Exception):
    pass

@dataclass
class Entry:
    id: str
    type: str = "note"
    title: str = ""
    body: str = ""
    tags: list[str] = field(default_factory=list)
    scope: str = "local"
    cwd: str | None = None
    status: str = "active"
    show_on_open: bool = True
    created: str = ""
    updated: str = ""

    @staticmethod
    def migrate(doc: dict) -> dict:
        d = dict(doc)
        d.setdefault("type", "note")
        d.setdefault("title", "")
        d.setdefault("body", "")
        d.setdefault("tags", [])
        d.setdefault("scope", "local")
        d.setdefault("cwd", None)
        d.setdefault("status", "active")
        d.setdefault("show_on_open", True)
        d.setdefault("created", "")
        d.setdefault("updated", "")
        d["schema_version"] = d.get("schema_version", 1)
        return d

    @classmethod
    def from_dict(cls, doc: dict) -> Entry:
        d = cls.migrate(doc)
        if not isinstance(d["id"], str) or not _ID_RE.fullmatch(d["id"]):
            raise ValueError(f"bad id {d['id']!r}")
        if d["scope"] not in ("global", "local"):
            raise ValueError(f"bad scope {d['scope']!r}")
        if d["status"] not in ("active", "done"):
            raise ValueError(f"bad status {d['status']!r}")
        if not isinstance(d["type"], str) or not d["type"]:
            raise ValueError(f"bad type {d['type']!r}")
        return cls(id=d["id"], type=d["type"], title=d["title"], body=d["body"],
                   tags=list(d["tags"]), scope=d["scope"], cwd=d["cwd"],
                   status=d["status"], show_on_open=bool(d["show_on_open"]),
                   created=d["created"], updated=d["updated"])

    def to_dict(self) -> dict:
        return {"id": self.id, "type": self.type, "title": self.title,
                "body": self.body, "tags": list(self.tags), "scope": self.scope,
                "cwd": self.cwd, "status": self.status,
                "show_on_open": self.show_on_open, "created": self.created,
                "updated": self.updated, "schema_version": SCHEMA_VERSION}

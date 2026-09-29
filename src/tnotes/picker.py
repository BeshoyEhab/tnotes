"""Picker rows (Task 5 stub: format_row only; Task 6 adds build_rows/run_picker)."""


def format_row(entry: dict) -> str:
    icons = {"url": "🔗", "cmd": "$", "note": "📝"}
    icon = icons.get(entry.get("type"), "📝")
    tags = f" [{','.join(entry.get('tags', []))}]" if entry.get("tags") else ""
    scope = "G" if entry.get("scope") == "global" else "·"
    done = "✔ " if entry.get("status") == "done" else ""
    return f"{done}{icon} {entry.get('title', '')}{tags} {scope}".rstrip()

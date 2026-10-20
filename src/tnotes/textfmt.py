"""Small text helpers shared by the CLI and TUI previews."""

import re


_FENCE = re.compile(r"^\s*(```|~~~)")
_THEMATIC = re.compile(r"^\s{0,3}([-*_])(?:\s*\1){2,}\s*$")


def preserve_linebreaks(text: str) -> str:
    """Turn single newlines into Markdown hard breaks.

    Markdown treats a lone newline as a soft break and renders the lines as
    one paragraph. Notes are line-oriented, so previews should keep the
    author's line breaks. Blank lines stay paragraph breaks; fenced and
    indented code blocks are left untouched.
    """
    if "\n" not in text:
        return text
    trailing = "\n" if text.endswith("\n") else ""
    lines = text.splitlines()
    output: list[str] = []
    in_fence = False
    fence_marker = ""
    for i, line in enumerate(lines):
        fence = _FENCE.match(line)
        if fence:
            marker = fence.group(1)
            if not in_fence:
                in_fence, fence_marker = True, marker
            elif marker == fence_marker:
                in_fence = False
            output.append(line)
            continue
        next_line = lines[i + 1] if i + 1 < len(lines) else ""
        code_indent = line.startswith("    ")
        if (not in_fence and not code_indent and not _THEMATIC.match(line)
                and line.strip() and next_line.strip()):
            output.append(line + "  ")
        else:
            output.append(line)
    return "\n".join(output) + trailing

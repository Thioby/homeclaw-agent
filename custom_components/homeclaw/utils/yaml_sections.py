"""YAML section manipulation utilities for Homeclaw.

Provides functions for removing top-level YAML sections from raw text
while preserving anchors, aliases, comments, and formatting.
"""

from __future__ import annotations

import re


def remove_yaml_section(content: str, key: str) -> str:
    """Remove a top-level YAML section from raw text.

    Finds ``key:`` at column 0 and removes all subsequent indented / blank /
    in-section-comment lines until the next top-level key or EOF.  Uses regex
    to avoid prefix collisions (e.g. ``notify`` vs ``notify_group``).

    If the section defines YAML anchors (``&name``) that are referenced
    elsewhere in the file via aliases (``*name``), removal is refused to
    prevent orphaned aliases that would make the YAML unparseable.

    Args:
        content: Raw YAML text.
        key: Top-level key to remove.

    Returns:
        Content with the section removed.

    Raises:
        ValueError: If the section defines a YAML anchor that is
            referenced by an alias elsewhere in the file.
    """
    key_pattern = re.compile(rf"^{re.escape(key)}:(\s|$)")
    lines = content.split("\n")

    # --- Anchor-safety check ---
    _check_anchor_safety(lines, key, key_pattern)

    # --- Normal removal ---
    result: list[str] = []
    skip = False

    for i, line in enumerate(lines):
        stripped = line.lstrip()

        if stripped and not line.startswith((" ", "\t")):
            if stripped.startswith("#"):
                if skip:
                    if _next_content_is_indented(lines, i + 1):
                        continue
                    skip = False
            elif key_pattern.match(stripped):
                skip = True
                continue
            else:
                skip = False

        if not skip:
            result.append(line)

    text = "\n".join(result)
    while "\n\n\n" in text:
        text = text.replace("\n\n\n", "\n\n")
    return text


def _next_content_is_indented(lines: list[str], start: int) -> bool:
    """Check if the next non-blank, non-comment line is indented.

    Used during section removal to decide whether a column-0 comment
    belongs to the section being removed (next content is indented) or
    to the following section (next content is a top-level key).

    Args:
        lines: All lines of the file.
        start: Index to start scanning from.

    Returns:
        True if the next meaningful line is indented (part of current section).
    """
    for j in range(start, len(lines)):
        s = lines[j].strip()
        if not s:
            continue
        if s.startswith("#") and not lines[j].startswith((" ", "\t")):
            continue
        return lines[j].startswith((" ", "\t"))
    return False


def _check_anchor_safety(
    lines: list[str],
    key: str,
    key_pattern: re.Pattern[str],
) -> None:
    """Raise ``ValueError`` if removing *key* would orphan a YAML alias.

    Scans ALL lines of the target section (header + indented body) for
    anchor definitions (``&anchor-name``).  For each anchor found, the
    remaining content (everything **outside** the section) is checked for
    alias references (``*anchor-name``).

    Args:
        lines: All lines of the file (already split).
        key: Top-level key being removed.
        key_pattern: Compiled regex that matches the section header.

    Raises:
        ValueError: When an alias referencing the anchor exists outside
            the section.
    """
    section_lines = _collect_section_lines(lines, key_pattern)
    if not section_lines:
        return  # Section not found -- nothing to guard

    # Find ALL anchors in the section (header + nested lines)
    anchor_re = re.compile(r"&([\w-]+)")
    anchors: list[str] = []
    for line in section_lines:
        anchors.extend(anchor_re.findall(line))

    if not anchors:
        return  # No anchors defined -- safe to remove

    # Collect lines that are NOT part of the section being removed
    outside_lines = _collect_outside_lines(lines, key_pattern)
    remaining_text = "\n".join(outside_lines)

    for anchor_name in anchors:
        alias_pattern = re.compile(rf"\*{re.escape(anchor_name)}\b")
        if alias_pattern.search(remaining_text):
            raise ValueError(
                f"Cannot remove section '{key}': it defines anchor "
                f"'&{anchor_name}' referenced by alias '*{anchor_name}' "
                f"elsewhere in the file"
            )


def _collect_section_lines(
    lines: list[str],
    key_pattern: re.Pattern[str],
) -> list[str]:
    """Return all lines belonging to the section matched by *key_pattern*.

    Includes the header line and all subsequent indented / blank /
    in-section-comment lines.

    Args:
        lines: All lines of the file.
        key_pattern: Compiled regex matching the section header.

    Returns:
        Lines inside the target section (empty list if not found).
    """
    section: list[str] = []
    inside = False

    for i, line in enumerate(lines):
        stripped = line.lstrip()

        if stripped and not line.startswith((" ", "\t")):
            if stripped.startswith("#"):
                if inside:
                    if _next_content_is_indented(lines, i + 1):
                        section.append(line)
                        continue
                    # Comment belongs to next section -- stop
                    break
                continue
            if key_pattern.match(stripped):
                inside = True
                section.append(line)
                continue
            if inside:
                break  # Next top-level key -- end of section
            continue

        if inside:
            section.append(line)

    return section


def _collect_outside_lines(
    lines: list[str],
    key_pattern: re.Pattern[str],
) -> list[str]:
    """Return lines that are NOT part of the section matched by *key_pattern*.

    Args:
        lines: All lines of the file.
        key_pattern: Compiled regex matching the section header.

    Returns:
        Lines outside the target section.
    """
    outside: list[str] = []
    skip = False

    for i, line in enumerate(lines):
        stripped = line.lstrip()

        if stripped and not line.startswith((" ", "\t")):
            if stripped.startswith("#"):
                if skip and _next_content_is_indented(lines, i + 1):
                    continue
                if skip:
                    skip = False
            elif key_pattern.match(stripped):
                skip = True
                continue
            else:
                skip = False

        if not skip:
            outside.append(line)

    return outside

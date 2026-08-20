from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).parents[1]
MARKDOWN_TARGET = re.compile(r"!?\[[^\]]*\]\(([^)\s]+)(?:\s+[^)]*)?\)")
HTML_TARGET = re.compile(r"\b(?:src|srcset)=\"([^\"]+)\"")


def _documentation_files() -> tuple[Path, ...]:
    return (ROOT / "README.md", *sorted((ROOT / "docs").rglob("*.md")))


def _local_targets(path: Path) -> tuple[str, ...]:
    source = path.read_text(encoding="utf-8")
    targets = [*MARKDOWN_TARGET.findall(source), *HTML_TARGET.findall(source)]
    return tuple(
        target
        for target in targets
        if not target.startswith(("#", "http://", "https://", "mailto:"))
    )


def test_documentation_links_and_images_resolve_inside_repository() -> None:
    broken: list[str] = []
    for document in _documentation_files():
        for raw_target in _local_targets(document):
            target = unquote(raw_target.split("#", maxsplit=1)[0].strip("<>"))
            resolved = (document.parent / target).resolve()
            try:
                resolved.relative_to(ROOT)
            except ValueError:
                broken.append(f"{document.relative_to(ROOT)} -> {raw_target} escapes repository")
                continue
            if not resolved.exists():
                broken.append(f"{document.relative_to(ROOT)} -> {raw_target} does not exist")

    assert not broken, "\n".join(broken)

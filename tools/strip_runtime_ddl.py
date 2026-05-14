"""Replace database/* _ensure_schema() that contain CREATE TABLE with no-ops."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "database"


def strip_file(path: Path) -> bool:
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    if not any("CREATE TABLE IF NOT EXISTS" in ln for ln in lines):
        return False
    out: list[str] = []
    i = 0
    changed = False
    while i < len(lines):
        line = lines[i]
        if line.startswith("def _ensure_schema() -> None:"):
            out.append(line)
            out.append('    """Schema from Alembic only; no runtime DDL."""\n')
            out.append("    return\n")
            i += 1
            changed = True
            while i < len(lines):
                l = lines[i]
                if l.strip() == "":
                    i += 1
                    continue
                if not l.startswith((" ", "\t")) and (
                    l.startswith("def ")
                    or l.startswith("class ")
                    or l.startswith("@")
                ):
                    break
                i += 1
            continue
        out.append(line)
        i += 1
    if changed:
        path.write_text("".join(out), encoding="utf-8")
    return changed


def main() -> None:
    changed = []
    for p in sorted(ROOT.glob("*.py")):
        if strip_file(p):
            changed.append(p.name)
    print("Stripped:", ", ".join(changed) if changed else "(none)")


if __name__ == "__main__":
    main()

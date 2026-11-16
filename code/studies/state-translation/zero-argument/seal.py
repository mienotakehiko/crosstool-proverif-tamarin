"""Seal kit sources and models, never mutable run directories."""
from pathlib import Path
from common import dump, sha

ROOT = Path(__file__).resolve().parent


def main():
    files = [p for p in ROOT.iterdir() if p.is_file() and p.suffix in (".py", ".sh", ".md", ".json", ".txt")
             and p.name not in ("KIT_HASHES.json", "DELIVERY_HASHES.json")]
    files += list((ROOT / "models").glob("*"))
    dump(ROOT / "KIT_HASHES.json", {str(p.relative_to(ROOT)): sha(p) for p in sorted(files)})


if __name__ == "__main__":
    main()

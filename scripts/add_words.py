import json
import sys
from pathlib import Path

WORDS = Path(__file__).resolve().parent.parent / "data" / "words.json"


def main(path: str) -> None:
    items = json.loads(WORDS.read_text(encoding="utf-8"))
    seen = {i["en"].lower() for i in items}
    added = 0
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if ":" not in line:
            continue
        en, ru = (part.strip() for part in line.split(":", 1))
        if en and ru and en.lower() not in seen:
            seen.add(en.lower())
            items.append({"en": en.lower(), "ru": ru})
            added += 1
    WORDS.write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"added {added}, total {len(items)}")


if __name__ == "__main__":
    main(sys.argv[1])

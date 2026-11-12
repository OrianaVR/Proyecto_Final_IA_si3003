import csv
import json
import re
from pathlib import Path
from .json_store import write_json
from .provenance import file_hash


def normalized_text(text: str) -> str:
    return re.sub(r"[ \t]+", " ", text).strip()


def extract_pdf(path: Path) -> list[tuple[int, str]]:
    from pypdf import PdfReader
    pages = []
    for number, page in enumerate(PdfReader(path).pages, 1):
        text = normalized_text(page.extract_text() or "")
        if text:
            pages.append((number, text))
    return pages


def extract_html(path: Path) -> list[tuple[None, str]]:
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(path.read_bytes(), "html.parser")
    for element in soup.select("script, style, nav, header, footer, noscript, svg, form"):
        element.decompose()
    main = soup.find("main") or soup.find(attrs={"role": "main"}) or soup.body or soup
    text = normalized_text(main.get_text(separator="\n", strip=True))
    return [(None, text)] if text else []


def prepare_corpus(root: Path) -> dict:
    sources = json.loads((root / "config/corpus_sources.json").read_text(encoding="utf-8"))
    records, manifest = [], []
    for source in sources:
        raw = root / "corpus/raw" / source["filename"]
        sidecar = json.loads(raw.with_suffix(raw.suffix+".source.json").read_text(encoding="utf-8"))
        if file_hash(raw) != sidecar["sha256"]:
            raise ValueError(f"Hash no coincide: {raw}")
        pages = extract_pdf(raw) if source["format"] == "pdf" else extract_html(raw)
        if sum(len(text.split()) for _, text in pages) < 80:
            raise ValueError(f"Contenido insuficiente para RAG: {raw}")
        text_path = root / "corpus/text" / f"{source['id']}.txt"
        text_path.parent.mkdir(parents=True, exist_ok=True)
        text_path.write_text("\n\n".join(
            f"[Página {number}]\n{text}" if number else text for number, text in pages)+"\n", encoding="utf-8")
        for number, text in pages:
            records.append({"document_id": source["id"], "title": source["title"],
                            "url": source["url"], "page_number": number, "text": text,
                            "retrieved_at_utc": sidecar["retrieved_at_utc"],
                            "version_note": source["version_note"]})
        manifest.append({**source, **sidecar, "raw_path": str(raw.relative_to(root)),
                         "text_path": str(text_path.relative_to(root)),
                         "text_sha256": file_hash(text_path), "nonempty_pages": len(pages),
                         "word_count": sum(len(text.split()) for _, text in pages)})
    target = root / "corpus/documents.jsonl"
    target.write_text("".join(json.dumps(record, ensure_ascii=False)+"\n" for record in records), encoding="utf-8")
    write_json(root / "corpus/manifest.json", manifest)
    with (root / "corpus/sources.csv").open("w", encoding="utf-8", newline="") as handle:
        columns = ["id", "title", "url", "retrieved_at_utc", "format", "raw_path", "text_path", "sha256", "word_count", "version_note"]
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(manifest)
    return {"document_count": len(manifest), "record_count": len(records),
            "word_count": sum(item["word_count"] for item in manifest)}

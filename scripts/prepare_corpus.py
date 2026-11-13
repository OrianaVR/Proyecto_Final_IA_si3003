import argparse
import json
from src.config import PROJECT_ROOT
from src.infrastructure.corpus import prepare_corpus
from src.infrastructure.http_client import download
from src.infrastructure.provenance import record_download


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download", action="store_true")
    args = parser.parse_args()
    if args.download:
        sources = json.loads((PROJECT_ROOT / "config/corpus_sources.json").read_text(encoding="utf-8"))
        for source in sources:
            path = PROJECT_ROOT / "corpus/raw" / source["filename"]
            download(source["url"], path)
            record_download(path, source["url"])
    print(json.dumps(prepare_corpus(PROJECT_ROOT), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

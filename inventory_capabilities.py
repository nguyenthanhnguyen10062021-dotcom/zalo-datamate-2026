"""Freeze development grammar selection without reading answers or legacy results."""
import argparse
import json
from pathlib import Path

from verification.manifest import build_manifest, inventory_summary, local_output, write_json


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--train', type=Path, default=Path('train'))
    parser.add_argument('--out', type=Path, default=Path('reports/capability_inventory/manifest.json'))
    args = parser.parse_args(argv)
    out = local_output(args.out, (args.train/'questions.jsonl', args.train/'rulebook.md'))
    if out.exists():
        parser.error('manifest already exists; use a new output path to keep the frozen inventory')
    manifest = build_manifest(args.train/'questions.jsonl', args.train/'rulebook.md')
    write_json(out, manifest)
    print(json.dumps(inventory_summary(manifest), ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

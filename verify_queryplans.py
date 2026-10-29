"""Verify frozen retrospective QueryPlans independently of the legacy selector/calculator."""
import argparse
import json
from pathlib import Path

from verification.manifest import ManifestError, local_output, write_json
from verification.runner import verification_exit_code, verify_manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--train', type=Path, default=Path('train'))
    parser.add_argument('--cache', type=Path, default=Path('cache'))
    parser.add_argument('--out', type=Path, default=Path('reports/capability_inventory/verification.json'))
    args = parser.parse_args(argv)
    out = local_output(args.out, (args.manifest,))
    markdown = local_output(out.with_suffix('.md'), (args.manifest,))
    if out.suffix != '.json' or any(path.is_relative_to(folder.resolve()) for path in (out, markdown)
                                  for folder in (args.train, args.cache)):
        raise ManifestError('report must be .json outside the input corpus/cache directories')
    if out.exists() or markdown.exists():
        parser.error('report already exists; use a new output path to preserve prior evidence')
    def progress(done, total, count):
        print(f'Executed {done}/{total} cache groups, {count} selected plans.', flush=True)
    result = verify_manifest(args.manifest, args.train, args.cache, progress=progress)
    write_json(out, result)
    summary = {k: v for k, v in result.items() if k not in
               ('rows', 'cache_sha256', 'code_sha256')}
    markdown.write_text('# Retrospective grammar + QueryExecutor verification\n\n'
        'Not full-train PA, model accuracy, or an unseen holdout. All selected failures remain counted.\n\n'
        '```json\n' + json.dumps(summary, ensure_ascii=False, indent=2) + '\n```\n', encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return verification_exit_code(result)


if __name__ == '__main__':
    raise SystemExit(main())

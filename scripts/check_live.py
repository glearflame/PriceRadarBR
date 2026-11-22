"""Run a real marketplace search and save exactly what the adapters returned."""
import argparse
import json
import sys
import threading
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from priceradar.scraper import run


def main():
    parser = argparse.ArgumentParser(description='Validate PriceRadar BR against live marketplace pages.')
    parser.add_argument('query', help='product name and model, for example: teclado logitech k380')
    parser.add_argument('--output', type=Path, help='write the complete report as JSON')
    args = parser.parse_args()
    report = {
        'query': args.query,
        'started_at': datetime.now().astimezone().isoformat(timespec='seconds'),
        'stores': {},
        'events': [],
    }

    def emit(kind, value):
        if kind == 'store':
            store, offers, message = value
            report['stores'][store] = {
                'message': message,
                'count': len(offers),
                'offers': [asdict(offer) for offer in offers],
            }
            print(f'{store}: {len(offers)} ofertas — {message}', flush=True)
        elif kind != 'status':
            report['events'].append({'kind': kind, 'value': value})
            if kind == 'error':
                print(f'ERRO: {value}', file=sys.stderr, flush=True)

    run(args.query, emit, threading.Event())
    report['finished_at'] = datetime.now().astimezone().isoformat(timespec='seconds')
    report['total_offers'] = sum(store['count'] for store in report['stores'].values())
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(f'Relatório: {args.output.resolve()}')
    return 0 if report['total_offers'] else 2


if __name__ == '__main__':
    raise SystemExit(main())

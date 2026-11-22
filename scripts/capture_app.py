"""Capture the real desktop UI under a graphical display or Xvfb."""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from priceradar.app import App
from priceradar.core import Offer


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--offers', type=Path, help='live-validation.json produced by check_live.py')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    app = App()
    try:
        app.geometry('1220x820+0+0')
        if args.offers:
            report = json.loads(args.offers.read_text(encoding='utf-8'))
            offers = [Offer(**item) for store in report['stores'].values() for item in store['offers']]
            app.offers = offers
            app.show_offers(offers)
            app.notify(f"Coleta real de {report['started_at']} — {len(offers)} ofertas")
        app.update_idletasks()
        time.sleep(1)
        app.update_idletasks()
        from PIL import ImageGrab
        args.output.parent.mkdir(parents=True, exist_ok=True)
        x, y = app.winfo_rootx(), app.winfo_rooty()
        image = ImageGrab.grab(bbox=(x, y, x + app.winfo_width(), y + app.winfo_height()))
        image.save(args.output)
        print(args.output.resolve())
    finally:
        app.close()


if __name__ == '__main__':
    main()

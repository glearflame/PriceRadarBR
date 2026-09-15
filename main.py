import multiprocessing, logging, os, sys
from pathlib import Path
from logging.handlers import RotatingFileHandler

def main():
    root=Path(os.getenv('LOCALAPPDATA',Path.home()/'.local/share'))/'PriceRadarBR'; root.mkdir(parents=True,exist_ok=True)
    logging.basicConfig(level=logging.INFO,handlers=[RotatingFileHandler(root/'app.log',maxBytes=1_000_000,backupCount=2,encoding='utf-8')],format='%(asctime)s %(levelname)s %(message)s')
    if '--self-test' in sys.argv:
        from priceradar.core import money
        assert money('R$ 1.234,56')==123456
        import customtkinter, undetected_chromedriver, openpyxl, reportlab, PIL
        return
    from priceradar.app import App
    App().mainloop()

if __name__=='__main__':
    multiprocessing.freeze_support()
    main()

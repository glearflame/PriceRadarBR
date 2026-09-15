from dataclasses import dataclass, asdict
from decimal import Decimal, InvalidOperation
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse, urljoin
import os, sqlite3, json, re

STORES = {'Mercado Livre': ('mercadolivre.com.br', 'mercadolivre.com'), 'Amazon': ('amazon.com.br',), 'Shopee': ('shopee.com.br',)}

def valid_url(url, store=None):
    try:
        p = urlparse(url)
        port = p.port
    except ValueError:
        return False
    domains = STORES[store] if store else sum(STORES.values(), ())
    return p.scheme == 'https' and not p.username and port in (None, 443) and any(p.hostname == d or (p.hostname or '').endswith('.'+d) for d in domains)

def money(value):
    s = re.sub(r'[^\d,.]', '', str(value))
    if ',' in s: s = s.replace('.', '').replace(',', '.')
    elif s.count('.') > 1: s = s.replace('.', '')
    try:
        n = Decimal(s)
        return int(n * 100) if n > 0 else None
    except InvalidOperation: return None

def brl(cents):
    return ('R$ {:,.2f}'.format(cents/100)).replace(',', 'X').replace('.', ',').replace('X', '.')

@dataclass
class Offer:
    store: str
    title: str
    cents: int
    url: str
    captured: str = ''
    def __post_init__(self):
        if not self.captured: self.captured = datetime.now().astimezone().isoformat(timespec='seconds')

class Database:
    def __init__(self, path=None):
        root = Path(os.getenv('LOCALAPPDATA', Path.home()/'.local/share'))/'PriceRadarBR'
        if path is None:
            root.mkdir(parents=True, exist_ok=True)
            path = root/'radar.sqlite3'
        self.path = path
        with self.connect() as db:
            db.executescript('CREATE TABLE IF NOT EXISTS history(id INTEGER PRIMARY KEY, query TEXT, created TEXT, offers TEXT); CREATE TABLE IF NOT EXISTS favorites(url TEXT PRIMARY KEY, offer TEXT); CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT);')
    def connect(self): return sqlite3.connect(self.path, timeout=10)
    def save(self, query, offers):
        with self.connect() as db:
            db.execute('INSERT INTO history(query,created,offers) VALUES(?,?,?)', (query, datetime.now().isoformat(timespec='seconds'),json.dumps([asdict(o) for o in offers])))
            db.execute('DELETE FROM history WHERE id NOT IN (SELECT id FROM history ORDER BY id DESC LIMIT 100)')
    def history(self):
        with self.connect() as db: return db.execute('SELECT query,created,offers FROM history ORDER BY id DESC').fetchall()
    def favorites(self):
        with self.connect() as db: return [Offer(**json.loads(r[0])) for r in db.execute('SELECT offer FROM favorites')]
    def toggle(self, offer):
        with self.connect() as db:
            found = db.execute('SELECT 1 FROM favorites WHERE url=?',(offer.url,)).fetchone()
            if found: db.execute('DELETE FROM favorites WHERE url=?',(offer.url,))
            else: db.execute('INSERT INTO favorites VALUES(?,?)',(offer.url,json.dumps(asdict(offer))))
        return not found
    def setting(self,key,value=None):
        with self.connect() as db:
            if value is not None: db.execute('INSERT OR REPLACE INTO settings VALUES(?,?)',(key,value))
            row=db.execute('SELECT value FROM settings WHERE key=?',(key,)).fetchone()
            return row[0] if row else None

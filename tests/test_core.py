import sqlite3, tempfile, unittest
from pathlib import Path
from priceradar.core import Database, Offer, money, valid_url
from priceradar.scraper import parse, relevant, headless_enabled, diagnose_page, should_stop_waiting, should_retry_page, canonical_url
from priceradar.exporters import export_file

class CoreTests(unittest.TestCase):
    def test_brazilian_money(self):
        for raw,want in [('R$ 1.234,56',123456),('49,90',4990),('1299.99',129999),('indisponível',None),('0',None)]: self.assertEqual(money(raw),want)
    def test_domains(self):
        self.assertTrue(valid_url('https://www.amazon.com.br/dp/ABC'))
        for bad in ['https://amazon.com.br.evil.test/x','http://amazon.com.br','https://evil.test','https://user@amazon.com.br','https://amazon.com.br:bad']:
            self.assertFalse(valid_url(bad))
    def test_connections_close_after_use(self):
        with tempfile.TemporaryDirectory() as d:
            db=Database(Path(d)/'db')
            with db.connect() as connection:
                connection.execute('SELECT 1')
            with self.assertRaises(sqlite3.ProgrammingError):
                connection.execute('SELECT 1')
    def test_storage(self):
        with tempfile.TemporaryDirectory() as d:
            db=Database(Path(d)/'db'); offer=Offer('Amazon','Produto',12990,'https://amazon.com.br/dp/X')
            self.assertTrue(db.toggle(offer)); self.assertEqual(db.favorites()[0].cents,12990)
            self.assertFalse(db.toggle(offer)); self.assertEqual(db.favorites(),[])
            db.save('teste',[offer]); self.assertEqual(db.history()[0][0],'teste')
    def test_marketplace_parsers(self):
        cases=[('Amazon','<div data-component-type="s-search-result"><a href="/dp/X"><h2>Teclado K380</h2></a><span class="a-price"><span class="a-offscreen">R$ 199,90</span></span></div>','https://amazon.com.br',19990),('Mercado Livre','<li class="ui-search-layout__item"><a class="poly-component__title" href="https://produto.mercadolivre.com.br/MLB-123">Teclado K380</a><div class="poly-price__current"><span class="andes-money-amount"><span class="andes-money-amount__fraction">1.299</span><span class="andes-money-amount__cents">99</span></span></div></li>','https://mercadolivre.com.br',129999),('Shopee','<div class="shopee-search-item-result__item"><a href="/teclado-i.123.456"><div data-sqe="name">Teclado K380</div><div data-sqe="price">R$ 149,90</div></a></div>','https://shopee.com.br',14990)]
        for store,html,url,cents in cases:
            offers=parse(html,store,url); self.assertEqual(len(offers),1); self.assertEqual(offers[0].cents,cents)
            self.assertTrue(relevant(offers[0],'teclado K380'))
        self.assertEqual(parse('<html>CAPTCHA</html>','Amazon','https://amazon.com.br'),[])
    def test_block_and_store_error_pages_are_diagnosed(self):
        self.assertEqual(diagnose_page('<html>Verificação de tráfego</html>','https://shopee.com.br/verify/traffic/error'),'blocked')
        self.assertEqual(diagnose_page('<html>CAPTCHA</html>','https://www.amazon.com.br/s?k=teste'),'blocked')
        self.assertEqual(diagnose_page('<html>Olá! Para continuar, acesse sua conta</html>','https://www.mercadolivre.com.br/gz/account-verification'),'blocked')
        self.assertEqual(diagnose_page('<html>Hubo un error accediendo a esta pagina</html>','https://lista.mercadolivre.com.br/teste'),'store_error')
        self.assertEqual(diagnose_page('<html>Nenhum resultado</html>','https://www.amazon.com.br/s?k=inexistente'),'empty')
    def test_numeric_model_must_match_instead_of_generic_brand_tokens(self):
        self.assertFalse(relevant(Offer('Amazon','Teclado Logitech K250',10000,'https://amazon.com.br/dp/X'),'teclado logitech k380'))
        self.assertFalse(relevant(Offer('Amazon','Combo Teclado e Mouse Logitech',10000,'https://amazon.com.br/dp/X'),'teclado logitech k380'))
        self.assertTrue(relevant(Offer('Amazon','Teclado Logitech Pebble Keys 2 K380s',10000,'https://amazon.com.br/dp/X'),'teclado logitech k380'))
        self.assertFalse(relevant(Offer('Amazon','Placa RTX 3060 Ti',10000,'https://amazon.com.br/dp/X'),'RTX 4060'))
        self.assertTrue(relevant(Offer('Amazon','Placa RTX 4060 Ti',10000,'https://amazon.com.br/dp/X'),'RTX 4060'))
        self.assertTrue(relevant(Offer('Amazon','Placa RTX 4060 Ti',10000,'https://amazon.com.br/dp/X'),'RTX 4060 Ti'))
    def test_single_digit_numeric_model_must_match(self):
        cases=[('Logitech MX Keys 3','Logitech MX Keys 2','Logitech MX Keys 3'),('Apple iPhone 8','Apple iPhone 15','Apple iPhone 8')]
        for query,wrong_title,correct_title in cases:
            with self.subTest(query=query):
                self.assertFalse(relevant(Offer('Amazon',wrong_title,10000,'https://amazon.com.br/dp/X'),query))
                self.assertTrue(relevant(Offer('Amazon',correct_title,10000,'https://amazon.com.br/dp/X'),query))
    def test_only_truncated_empty_responses_are_retried_once(self):
        self.assertTrue(should_retry_page('<html></html>','https://amazon.com.br',0,0))
        self.assertFalse(should_retry_page('<html></html>','https://amazon.com.br',0,1))
        self.assertFalse(should_retry_page('<html>Nenhum resultado</html>'*1000,'https://amazon.com.br',0,0))
        self.assertFalse(should_retry_page('<html>CAPTCHA</html>','https://amazon.com.br',0,0))
        self.assertFalse(should_retry_page('<html></html>','https://amazon.com.br',1,0))
    def test_wait_stops_for_results_or_known_failures_not_empty_pages(self):
        self.assertTrue(should_stop_waiting('<html></html>','https://amazon.com.br',1))
        self.assertTrue(should_stop_waiting('<html>CAPTCHA</html>','https://amazon.com.br',0))
        self.assertTrue(should_stop_waiting('<html>Hubo un error accediendo</html>','https://lista.mercadolivre.com.br',0))
        self.assertFalse(should_stop_waiting('<html>Carregando</html>','https://amazon.com.br',0))
    def test_headless_mode_is_explicit_or_auto_detected(self):
        self.assertTrue(headless_enabled({'PRICERADAR_HEADLESS':'1'},'linux'))
        self.assertFalse(headless_enabled({'PRICERADAR_HEADLESS':'0'},'linux'))
        self.assertTrue(headless_enabled({},'linux'))
        self.assertFalse(headless_enabled({'DISPLAY':':0'},'linux'))
        self.assertFalse(headless_enabled({},'win32'))
    def test_amazon_sponsored_redirect_is_canonicalized(self):
        url='https://www.amazon.com.br/sspa/click?ie=UTF8&amp;url=%2FLogitech%2Fdp%2FB0CJ3WFW9H%2Fref%3Dsr_1_1_sspa%3Fkeywords%3Dk380'
        self.assertEqual(canonical_url(url.replace('&amp;','&'),'Amazon'),'https://www.amazon.com.br/dp/B0CJ3WFW9H')
    def test_amazon_tracking_urls_are_canonicalized_and_deduplicated(self):
        html='''<div>
        <div data-component-type="s-search-result"><a href="/dp/B0CJ3WFW9H/ref=sr_1_1?keywords=k380"><h2>Teclado K380</h2></a><span class="a-price"><span class="a-offscreen">R$ 149,90</span></span></div>
        <div data-component-type="s-search-result"><a href="https://www.amazon.com.br/dp/B0CJ3WFW9H?keywords=k380&amp;sr=8-2"><h2>Teclado K380</h2></a><span class="a-price"><span class="a-offscreen">R$ 149,90</span></span></div>
        </div>'''
        offers=parse(html,'Amazon','https://www.amazon.com.br/s?k=k380')
        self.assertEqual(len(offers),1)
        self.assertEqual(offers[0].url,'https://www.amazon.com.br/dp/B0CJ3WFW9H')
    def test_exports(self):
        from openpyxl import load_workbook
        offers=[Offer('Amazon','=HYPERLINK("unsafe") & Teclado K380',19990,'https://amazon.com.br/dp/X')]
        with tempfile.TemporaryDirectory() as d:
            x=Path(d)/'export.xlsx'; p=Path(d)/'export.pdf'
            export_file(x,offers); export_file(p,offers)
            wb=load_workbook(x); self.assertEqual(wb.active['B2'].data_type,'s'); self.assertEqual(wb.active['C2'].value,199.9)
            self.assertTrue(p.read_bytes().startswith(b'%PDF'))

if __name__=='__main__': unittest.main()

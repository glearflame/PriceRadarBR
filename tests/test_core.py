import tempfile, unittest
from pathlib import Path
from priceradar.core import Database, Offer, money, valid_url
from priceradar.scraper import parse, relevant
from priceradar.exporters import export_file

class CoreTests(unittest.TestCase):
    def test_brazilian_money(self):
        for raw,want in [('R$ 1.234,56',123456),('49,90',4990),('1299.99',129999),('indisponível',None),('0',None)]: self.assertEqual(money(raw),want)
    def test_domains(self):
        self.assertTrue(valid_url('https://www.amazon.com.br/dp/ABC'))
        for bad in ['https://amazon.com.br.evil.test/x','http://amazon.com.br','https://evil.test','https://user@amazon.com.br','https://amazon.com.br:bad']:
            self.assertFalse(valid_url(bad))
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
    def test_exports(self):
        from openpyxl import load_workbook
        offers=[Offer('Amazon','=HYPERLINK("unsafe") & Teclado K380',19990,'https://amazon.com.br/dp/X')]
        with tempfile.TemporaryDirectory() as d:
            x=Path(d)/'export.xlsx'; p=Path(d)/'export.pdf'
            export_file(x,offers); export_file(p,offers)
            wb=load_workbook(x); self.assertEqual(wb.active['B2'].data_type,'s'); self.assertEqual(wb.active['C2'].value,199.9)
            self.assertTrue(p.read_bytes().startswith(b'%PDF'))

if __name__=='__main__': unittest.main()

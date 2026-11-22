import os
import unittest
from urllib.parse import quote


@unittest.skipUnless(os.getenv('PRICERADAR_LIVE') == '1', 'live marketplace test disabled')
class LiveMarketplaceTests(unittest.TestCase):
    def test_amazon_search_returns_real_offers(self):
        from priceradar.core import valid_url
        from priceradar.scraper import create_driver, parse, relevant

        driver = create_driver()
        try:
            query = 'teclado logitech k380'
            url = 'https://www.amazon.com.br/s?k=' + quote(query)
            driver.get(url)
            offers = [offer for offer in parse(driver.page_source, 'Amazon', url) if relevant(offer, query)]
            self.assertTrue(offers, 'Amazon returned no readable offers; inspect current selectors or blocking page')
            self.assertTrue(all(valid_url(offer.url, 'Amazon') for offer in offers))
            self.assertTrue(all(offer.cents > 0 for offer in offers))
        finally:
            driver.quit()


if __name__ == '__main__':
    unittest.main()

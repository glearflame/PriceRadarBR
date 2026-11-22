import os
import tempfile
import unittest
from unittest.mock import patch


@unittest.skipUnless(os.getenv('PRICERADAR_GUI_TESTS') == '1', 'set PRICERADAR_GUI_TESTS=1 with a graphical display')
class AppSmokeTests(unittest.TestCase):
    def test_main_views_render(self):
        from priceradar.app import App

        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {'LOCALAPPDATA': directory}):
            app = App()
            try:
                app.update_idletasks()
                self.assertEqual(app.title(), 'PriceRadar BR')
                self.assertEqual(app.heading.cget('text'), 'Encontre mais. Pague menos.')
                for page, heading in (
                    ('favorites', 'Seus favoritos'),
                    ('history', 'Últimas descobertas'),
                    ('settings', 'Do seu jeito'),
                    ('search', 'Encontre mais. Pague menos.'),
                ):
                    app.navigate(page)
                    app.update_idletasks()
                    self.assertEqual(app.heading.cget('text'), heading)
            finally:
                app.close()


if __name__ == '__main__':
    unittest.main()

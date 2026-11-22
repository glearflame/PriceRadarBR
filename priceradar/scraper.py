"""Public rendered HTML adapters. No private APIs, CAPTCHA solving or login automation."""
import logging, os, re, sys, time, unicodedata
from urllib.parse import parse_qs, quote, urljoin, urlparse
from bs4 import BeautifulSoup
from .core import Offer, money, valid_url

CONFIG = {
 'Mercado Livre': ('https://lista.mercadolivre.com.br/{}', '.ui-search-layout__item', '.poly-component__title, .ui-search-item__title', '.poly-price__current .andes-money-amount, .ui-search-price__second-line .andes-money-amount', 'a.poly-component__title, a.ui-search-link'),
 'Amazon': ('https://www.amazon.com.br/s?k={}', '[data-component-type="s-search-result"]', 'h2', '.a-price:not(.a-text-price) .a-offscreen', 'a:has(h2), h2 a'),
 'Shopee': ('https://shopee.com.br/search?keyword={}', '.shopee-search-item-result__item', '[data-sqe="name"], .line-clamp-2', r'[data-sqe="price"], .text-base\/5', 'a[href*="-i."]'),
}

def headless_enabled(env=None, platform=None):
    env = os.environ if env is None else env
    platform = sys.platform if platform is None else platform
    forced = env.get('PRICERADAR_HEADLESS')
    if forced in ('1', 'true', 'yes'):
        return True
    if forced in ('0', 'false', 'no'):
        return False
    return platform.startswith('linux') and not env.get('DISPLAY')

def diagnose_page(html, current_url):
    text = (html + ' ' + current_url).lower()
    if any(marker in text for marker in ('captcha', 'robot check', '/verify/traffic', 'account-verification', 'acesse sua conta', 'verificação de tráfego')):
        return 'blocked'
    if 'hubo un error accediendo' in text:
        return 'store_error'
    return 'empty'

def should_stop_waiting(html, current_url, card_count):
    return card_count > 0 or diagnose_page(html, current_url) != 'empty'

def should_retry_page(html, current_url, card_count, attempt):
    return attempt == 0 and card_count == 0 and len(html) < 10_000 and diagnose_page(html, current_url) == 'empty'

def create_driver():
    import shutil
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service

    options = webdriver.ChromeOptions()
    for argument in ('--lang=pt-BR', '--disable-notifications', '--disable-dev-shm-usage', '--window-size=1365,1000'):
        options.add_argument(argument)
    if headless_enabled():
        options.add_argument('--headless=new')
    binary = next((path for name in ('google-chrome-stable', 'google-chrome', 'chromium', 'chromium-browser') if (path := shutil.which(name))), None)
    if binary:
        options.binary_location = binary
    chromedriver = shutil.which('chromedriver')
    service = Service(chromedriver) if chromedriver else Service()
    return webdriver.Chrome(service=service, options=options)

def canonical_url(url, store):
    if store == 'Amazon':
        parsed = urlparse(url)
        target = parse_qs(parsed.query).get('url', [None])[0]
        if target:
            parsed = urlparse(urljoin(url, target))
        match = re.search(r'/(?:dp|gp/product)/([A-Z0-9]{10})', parsed.path)
        if match:
            return f'https://{parsed.hostname}/dp/{match.group(1)}'
    return url

def parse(html, store, base):
    soup = BeautifulSoup(html, 'html.parser'); result=[]; seen=set()
    _, card_sel, title_sel, price_sel, link_sel = CONFIG[store]
    for card in soup.select(card_sel):
        title=card.select_one(title_sel); price=card.select_one(price_sel); link=card.select_one(link_sel)
        if not all((title,price,link)): continue
        # Mercado Livre visually splits whole reais and cents.
        whole=price.select_one('.andes-money-amount__fraction')
        if whole:
            fraction=price.select_one('.andes-money-amount__cents')
            raw=whole.get_text() + ',' + (fraction.get_text() if fraction else '00')
        else: raw=price.get_text(' ',strip=True)
        cents=money(raw); url=canonical_url(urljoin(base,link.get('href','')),store)
        if cents and valid_url(url,store) and url not in seen:
            seen.add(url); result.append(Offer(store,title.get_text(' ',strip=True),cents,url))
    return result[:18]

def relevant(offer, query):
    def norm(s): return ''.join(c for c in unicodedata.normalize('NFKD',s.lower()) if not unicodedata.combining(c))
    tokens=[t for t in re.findall(r'\w+',norm(query)) if len(t)>1 or t.isdigit()]
    text=norm(offer.title)
    text_tokens=re.findall(r'\w+',text)
    models=[t for t in tokens if any(c.isdigit() for c in t)]
    for model in models:
        if not any(candidate == model or (candidate.startswith(model) and candidate[len(model):].isalpha()) for candidate in text_tokens):
            return False
    return not tokens or sum(t in text for t in tokens)/len(tokens)>=.6

def run(query, emit, cancel):
    driver=None
    try:
        from selenium.webdriver.support.ui import WebDriverWait
        emit('status','Abrindo Chrome para consultar as lojas…')
        driver=create_driver()
        driver.set_page_load_timeout(35)
        if query.startswith(('http://','https://')):
            if not valid_url(query): raise ValueError('Cole um link HTTPS completo do Mercado Livre, Amazon Brasil ou Shopee.')
            driver.get(query)
            if not valid_url(driver.current_url): raise ValueError('O link redirecionou para um domínio não suportado.')
            WebDriverWait(driver,15).until(lambda d: d.find_elements('css selector','h1, #productTitle'))
            soup=BeautifulSoup(driver.page_source,'html.parser')
            title=soup.select_one('#productTitle, h1')
            query=title.get_text(' ',strip=True) if title else ''
            if not query: raise ValueError('Não foi possível identificar o produto. Busque pelo nome.')
            emit('query', query)
        for store,(template,card,*_) in CONFIG.items():
            if cancel.is_set(): break
            emit('status',f'Consultando {store}…')
            url=template.format(quote(query))
            try:
                for attempt in range(2):
                    driver.get(url)
                    deadline=time.monotonic()+18
                    while time.monotonic()<deadline and not cancel.is_set():
                        cards=driver.find_elements('css selector',card)
                        if should_stop_waiting(driver.page_source,driver.current_url,len(cards)): break
                        cancel.wait(.35)
                    if cancel.is_set(): break
                    cards=driver.find_elements('css selector',card)
                    if should_retry_page(driver.page_source,driver.current_url,len(cards),attempt):
                        emit('status',f'{store} respondeu uma página incompleta; tentando novamente…')
                        continue
                    break
                if cancel.is_set(): break
                offers=[o for o in parse(driver.page_source,store,url) if relevant(o,query)]
                if offers:
                    message='Concluído'
                else:
                    problem=diagnose_page(driver.page_source,driver.current_url)
                    message={
                        'blocked':'A loja pediu login, CAPTCHA ou verificação nesta conexão. Consulta não contornada.',
                        'store_error':'A loja retornou uma página de erro. Tente novamente mais tarde.',
                        'empty':'Sem ofertas legíveis. Pode não haver resultados ou os seletores mudaram.',
                    }[problem]
                emit('store',(store,offers,message))
            except Exception:
                logging.exception('Falha ao consultar %s',store)
                emit('store',(store,[],'Consulta indisponível. Abra a loja ou tente novamente.'))
    except Exception as e:
        logging.exception('Falha na busca')
        emit('error',str(e) if isinstance(e,ValueError) else 'Não foi possível iniciar a consulta. Verifique Chrome/Chromium e internet; o Selenium gerencia o driver automaticamente.')
    finally:
        if driver:
            try: driver.quit()
            except Exception: logging.exception('Fechamento do navegador')
        emit('done',cancel.is_set())

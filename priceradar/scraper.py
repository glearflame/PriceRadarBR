"""Public rendered HTML adapters. No private APIs, CAPTCHA solving or login automation."""
import logging, re, time, unicodedata
from urllib.parse import quote, urljoin
from bs4 import BeautifulSoup
from .core import Offer, money, valid_url

CONFIG = {
 'Mercado Livre': ('https://lista.mercadolivre.com.br/{}', '.ui-search-layout__item', '.poly-component__title, .ui-search-item__title', '.poly-price__current .andes-money-amount, .ui-search-price__second-line .andes-money-amount', 'a.poly-component__title, a.ui-search-link'),
 'Amazon': ('https://www.amazon.com.br/s?k={}', '[data-component-type="s-search-result"]', 'h2', '.a-price:not(.a-text-price) .a-offscreen', 'a:has(h2), h2 a'),
 'Shopee': ('https://shopee.com.br/search?keyword={}', '.shopee-search-item-result__item', '[data-sqe="name"], .line-clamp-2', r'[data-sqe="price"], .text-base\/5', 'a[href*="-i."]'),
}

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
        cents=money(raw); url=urljoin(base,link.get('href',''))
        if cents and valid_url(url,store) and url not in seen:
            seen.add(url); result.append(Offer(store,title.get_text(' ',strip=True),cents,url))
    return result[:18]

def relevant(offer, query):
    def norm(s): return ''.join(c for c in unicodedata.normalize('NFKD',s.lower()) if not unicodedata.combining(c))
    tokens=[t for t in re.findall(r'\w+',norm(query)) if len(t)>1]
    text=norm(offer.title)
    return not tokens or sum(t in text for t in tokens)/len(tokens)>=.6

def run(query, emit, cancel, version=None):
    driver=None
    try:
        import undetected_chromedriver as uc
        from selenium.webdriver.support.ui import WebDriverWait
        opts=uc.ChromeOptions(); opts.add_argument('--lang=pt-BR'); opts.add_argument('--disable-notifications')
        emit('status','Abrindo Chrome para consultar as lojas…')
        driver=uc.Chrome(options=opts, use_subprocess=True, version_main=version)
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
                driver.get(url)
                deadline=time.monotonic()+18
                while time.monotonic()<deadline and not cancel.is_set():
                    if driver.find_elements('css selector',card): break
                    cancel.wait(.35)
                if cancel.is_set(): break
                offers=[o for o in parse(driver.page_source,store,url) if relevant(o,query)]
                emit('store',(store,offers,'Concluído' if offers else 'Sem ofertas legíveis. Pode haver login, bloqueio ou mudança da página.'))
            except Exception:
                logging.exception('Falha ao consultar %s',store)
                emit('store',(store,[],'Consulta indisponível. Abra a loja ou tente novamente.'))
    except Exception as e:
        logging.exception('Falha na busca')
        emit('error',str(e) if isinstance(e,ValueError) else 'Não foi possível iniciar a consulta. Verifique Chrome, internet e a versão do ChromeDriver nas configurações.')
    finally:
        if driver:
            try: driver.quit()
            except Exception: logging.exception('Fechamento do navegador')
        emit('done',cancel.is_set())

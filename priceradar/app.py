import json, logging, queue, threading, webbrowser
from tkinter import filedialog, messagebox
import customtkinter as ctk
from PIL import Image, ImageDraw
from .core import Database, Offer, brl, valid_url
from .scraper import run, CONFIG
from .exporters import export_file

BG=('#F4F5FA','#0D0F14'); PANEL=('#FFFFFF','#151821'); BORDER=('#DFE3ED','#282D3B'); MUTED=('#626C80','#969FB4'); ACCENT='#7765F5'

class App(ctk.CTk):
    def __init__(self):
        super().__init__(); self.db=Database(); ctk.set_appearance_mode(self.db.setting('theme') or 'dark')
        self.title('PriceRadar BR'); self.geometry('1220x820'); self.minsize(980,690); self.configure(fg_color=BG)
        self.events=queue.Queue(); self.cancel=threading.Event(); self.busy=False; self.offers=[]; self.visible=[]; self.page='search'; self.resolved=''; self.closed=False
        self.grid_columnconfigure(1,weight=1); self.grid_rowconfigure(0,weight=1)
        side=ctk.CTkFrame(self,width=220,corner_radius=0,fg_color=PANEL); side.grid(row=0,column=0,sticky='nsew'); side.grid_propagate(False)
        logo=Image.new('RGBA',(52,52)); d=ImageDraw.Draw(logo); d.rounded_rectangle((0,0,51,51),radius=15,fill=ACCENT); d.ellipse((10,10,40,40),outline='white',width=2); d.ellipse((19,19,31,31),outline='white',width=2); d.line((25,25,40,12),fill='white',width=3)
        self.logo=ctk.CTkImage(logo,logo,size=(42,42)); ctk.CTkLabel(side,text='  PriceRadar',image=self.logo,compound='left',font=('Segoe UI',21,'bold')).pack(padx=20,pady=(32,3))
        ctk.CTkLabel(side,text='BRASIL  /  DESKTOP',font=('Segoe UI',10,'bold'),text_color=MUTED).pack(pady=(0,35))
        for label,page in [('⌕  Explorar preços','search'),('♡  Favoritos','favorites'),('◷  Histórico','history'),('⚙  Configurações','settings')]:
            ctk.CTkButton(side,text=label,anchor='w',height=43,fg_color='transparent',text_color=('#303647','#DCE0F0'),hover_color=BORDER,command=lambda p=page:self.navigate(p)).pack(fill='x',padx=16,pady=4)
        ctk.CTkLabel(side,text='Seu próximo achado,\npor um preço melhor.',justify='left',text_color=MUTED,font=('Segoe UI',13)).pack(side='bottom',padx=24,pady=30)
        self.main=ctk.CTkFrame(self,fg_color='transparent'); self.main.grid(row=0,column=1,sticky='nsew',padx=30,pady=26)
        self.main.grid_columnconfigure(0,weight=1); self.main.grid_rowconfigure(4,weight=1)
        self.heading=ctk.CTkLabel(self.main,text='Encontre mais. Pague menos.',font=('Segoe UI',29,'bold'),anchor='w'); self.heading.grid(row=0,column=0,sticky='ew')
        ctk.CTkLabel(self.main,text='Mercado Livre  ·  Shopee  ·  Amazon Brasil',text_color=MUTED,anchor='w').grid(row=1,column=0,sticky='ew',pady=(3,22))
        search=ctk.CTkFrame(self.main,fg_color=PANEL,border_width=1,border_color=BORDER,corner_radius=14); search.grid(row=2,column=0,sticky='ew'); search.grid_columnconfigure(0,weight=1)
        self.entry=ctk.CTkEntry(search,placeholder_text='Busque um produto ou cole o link completo…',height=50,border_width=0,fg_color='transparent',font=('Segoe UI',15)); self.entry.grid(row=0,column=0,sticky='ew',padx=12,pady=8)
        self.search_button=ctk.CTkButton(search,text='Comparar  ↗',height=42,width=125,fg_color=ACCENT,hover_color='#6351DC',command=self.search); self.search_button.grid(row=0,column=1,padx=10)
        toolbar=ctk.CTkFrame(self.main,fg_color='transparent'); toolbar.grid(row=3,column=0,sticky='ew',pady=(16,12))
        self.filter=ctk.CTkOptionMenu(toolbar,values=['Todas as lojas',*CONFIG],fg_color=PANEL,button_color=ACCENT,text_color=('#303647','#DCE0F0'),command=lambda _:self.show_offers(self.db.favorites() if self.page=='favorites' else self.offers)); self.filter.pack(side='left')
        for ext in ['pdf','xlsx']:
            ctk.CTkButton(toolbar,text=ext.upper()+'  ↓',width=72,fg_color=PANEL,text_color=('#303647','#DCE0F0'),hover_color=BORDER,command=lambda e=ext:self.export(e)).pack(side='right',padx=(8,0))
        self.content=ctk.CTkScrollableFrame(self.main,fg_color='transparent',corner_radius=0); self.content.grid(row=4,column=0,sticky='nsew'); self.content.grid_columnconfigure(0,weight=1)
        self.status=ctk.CTkLabel(self.main,text='Pronto para explorar  •  Ctrl+K para buscar',anchor='w',text_color=MUTED,font=('Segoe UI',12)); self.status.grid(row=5,column=0,sticky='ew',pady=(8,0))
        self.progress=ctk.CTkProgressBar(self.main,height=3,progress_color=ACCENT,mode='indeterminate'); self.progress.grid(row=6,column=0,sticky='ew',pady=(8,0)); self.progress.set(0)
        self.bind('<Control-k>',lambda _:self.entry.focus_set()); self.bind('<Return>',lambda _:self.search()); self.bind('<Escape>',lambda _:self.stop()); self.bind('<Control-e>',lambda _:self.export('xlsx')); self.protocol('WM_DELETE_WINDOW',self.close)
        self.empty(); self.after(100,self.poll)
    def notify(self,text): self.status.configure(text=text)
    def clear(self):
        for w in self.content.winfo_children(): w.destroy()
    def empty(self):
        self.clear()
        card=ctk.CTkFrame(self.content,fg_color=PANEL,corner_radius=20,border_width=1,border_color=BORDER); card.grid(row=0,column=0,sticky='ew',pady=20)
        for text,size,color in [('O preço certo começa aqui.',25,None),('Compare ofertas em três lojas, em um só lugar.',15,MUTED),('Digite marca + modelo para resultados mais relevantes.\nPreços não incluem frete nem cupons personalizados.',13,MUTED)]:
            ctk.CTkLabel(card,text=text,font=('Segoe UI',size),text_color=color or ('#252B3C','#ECEEFA')).pack(padx=25,pady=18)
        ctk.CTkButton(card,text='Experimentar: teclado Logitech K380',fg_color=ACCENT,command=lambda:self.example()).pack(pady=(8,28))
    def example(self): self.entry.delete(0,'end'); self.entry.insert(0,'teclado Logitech K380'); self.search()
    def navigate(self,page):
        self.page=page; self.filter.set('Todas as lojas')
        if page=='search':
            self.heading.configure(text='Encontre mais. Pague menos.'); self.show_offers(self.offers) if self.offers else self.empty()
        elif page=='favorites':
            self.heading.configure(text='Seus favoritos'); self.show_offers(self.db.favorites())
        elif page=='history':
            self.heading.configure(text='Últimas descobertas'); self.clear(); self.visible=[]
            rows=self.db.history()
            if not rows: ctk.CTkLabel(self.content,text='Suas buscas aparecerão aqui.').pack(pady=45)
            for q,date,data in rows:
                ctk.CTkButton(self.content,text=f'{date.replace("T","  ")}  ·  {q[:65]}',anchor='w',height=52,fg_color=PANEL,text_color=('#303647','#DCE0F0'),hover_color=BORDER,command=lambda q=q,d=data:self.restore(q,d)).pack(fill='x',pady=5)
        else: self.settings()
    def restore(self,q,data):
        self.entry.delete(0,'end'); self.entry.insert(0,q); self.offers=[Offer(**o) for o in json.loads(data)]; self.navigate('search'); self.notify('Histórico carregado. Preços antigos: compare novamente para atualizar.')
    def settings(self):
        self.heading.configure(text='Do seu jeito'); self.clear(); self.visible=[]
        ctk.CTkLabel(self.content,text='APARÊNCIA',text_color=MUTED).pack(anchor='w',pady=(18,8))
        theme=ctk.CTkSegmentedButton(self.content,values=['Escuro','Claro'],command=self.theme); theme.set('Escuro' if ctk.get_appearance_mode()=='Dark' else 'Claro'); theme.pack(anchor='w')
        ctk.CTkLabel(self.content,text='Versão principal do Chrome (opcional, ex.: 140)\nUse somente se houver incompatibilidade do driver.',justify='left').pack(anchor='w',pady=(28,8))
        version=ctk.CTkEntry(self.content,placeholder_text='Automática'); version.insert(0,self.db.setting('chrome') or ''); version.pack(anchor='w')
        def save():
            value=version.get().strip()
            if value and (not value.isdigit() or not 100<=int(value)<=999): self.notify('Informe uma versão válida ou deixe vazio.'); return
            self.db.setting('chrome',value); self.notify('Configuração salva.')
        ctk.CTkButton(self.content,text='Salvar',command=save,fg_color=ACCENT).pack(anchor='w',pady=12)
        ctk.CTkLabel(self.content,text='Ctrl+K  Buscar     Enter  Comparar     Esc  Cancelar     Ctrl+E  Excel\n\nAs consultas abrem uma janela do Chrome e não usam sua sessão pessoal.\nLogin ou CAPTCHA podem impedir a coleta; tente abrir a loja manualmente.\n\nHistórico e favoritos ficam apenas neste computador.\nResultados são candidatos: confira modelo, voltagem, tamanho e vendedor.',justify='left',text_color=MUTED).pack(anchor='w',pady=24)
    def theme(self,value):
        mode='dark' if value=='Escuro' else 'light'; ctk.set_appearance_mode(mode); self.db.setting('theme',mode)
    def search(self):
        if self.busy: self.stop(); return
        q=self.entry.get().strip()
        if not q: self.notify('Digite o produto ou cole um link para começar.'); self.entry.focus_set(); return
        if len(q)>1500: self.notify('Busca muito longa. Use o nome e modelo do produto.'); return
        if q.startswith(('http://','https://')) and not valid_url(q): self.notify('Use um link HTTPS completo de uma das três lojas.'); return
        self.offers=[]; self.visible=[]; self.resolved=q; self.cancel.clear(); self.busy=True; self.navigate('search'); self.clear()
        self.notify('Preparando consulta…'); self.search_button.configure(text='Cancelar'); self.progress.start(); self.store_messages=[]
        version=self.db.setting('chrome')
        threading.Thread(target=run,args=(q,lambda k,v:self.events.put((k,v)),self.cancel,int(version) if version else None),daemon=True).start()
    def stop(self):
        if self.busy: self.cancel.set(); self.notify('Cancelando… aguardando o navegador terminar a operação atual.')
    def poll(self):
        if self.closed: return
        try:
            while True:
                kind,value=self.events.get_nowait()
                if kind=='status': self.notify(value)
                elif kind=='query': self.resolved=value
                elif kind=='error': self.notify(value); self.store_messages.append(value)
                elif kind=='store':
                    store,offers,msg=value; self.offers.extend(offers); self.store_messages.append(f'{store}: {len(offers)} ofertas. {msg}')
                    if self.page=='search': self.show_offers(self.offers)
                elif kind=='done':
                    self.busy=False; self.search_button.configure(text='Comparar  ↗'); self.progress.stop(); self.progress.set(0)
                    if self.offers:
                        try: self.db.save(self.resolved,self.offers)
                        except Exception: logging.exception('Salvar histórico'); self.store_messages.append('Não foi possível salvar o histórico.')
                    self.notify(('Cancelado. ' if value else 'Consulta finalizada. ')+f'{len(self.offers)} ofertas coletadas.')
                    if self.page=='search':
                        self.show_offers(self.offers)
                        for msg in self.store_messages: ctk.CTkLabel(self.content,text=msg,wraplength=780,justify='left',text_color=MUTED).pack(anchor='w',pady=4)
        except queue.Empty: pass
        self.after(100,self.poll)
    def show_offers(self,offers):
        self.clear(); selected=self.filter.get()
        self.visible=sorted([o for o in offers if selected=='Todas as lojas' or o.store==selected],key=lambda o:o.cents)
        if not self.visible:
            ctk.CTkLabel(self.content,text='Nenhuma oferta disponível nesta visualização.',text_color=MUTED).pack(pady=35); return
        ctk.CTkLabel(self.content,text=f'{len(self.visible)} OFERTAS  /  MENOR PREÇO PRIMEIRO',text_color=MUTED,font=('Segoe UI',11,'bold')).pack(anchor='w',pady=(8,6))
        ctk.CTkLabel(self.content,text='Confira variações e frete. Resultados podem incluir acessórios e modelos diferentes.',wraplength=780,text_color=MUTED).pack(anchor='w',pady=(0,10))
        favorites={o.url for o in self.db.favorites()}
        for i,o in enumerate(self.visible):
            card=ctk.CTkFrame(self.content,fg_color=PANEL,border_width=2 if i==0 else 1,border_color=ACCENT if i==0 else BORDER,corner_radius=15); card.pack(fill='x',pady=6)
            card.grid_columnconfigure(0,weight=1)
            ctk.CTkLabel(card,text=o.store.upper()+('    •    MENOR PREÇO COLETADO' if i==0 else ''),font=('Segoe UI',10,'bold'),text_color=('#6452D8','#AF9CFF')).grid(row=0,column=0,sticky='w',padx=20,pady=(15,4))
            ctk.CTkLabel(card,text=o.title,wraplength=490,justify='left',anchor='w',font=('Segoe UI',15,'bold')).grid(row=1,column=0,sticky='ew',padx=20)
            ctk.CTkLabel(card,text='Consultado em '+o.captured[:19].replace('T','  '),text_color=MUTED,font=('Segoe UI',10)).grid(row=2,column=0,sticky='w',padx=20,pady=(8,15))
            ctk.CTkLabel(card,text=brl(o.cents),font=('Segoe UI',24,'bold'),text_color=('#23805A','#66DFB1') if i==0 else ('#202637','#F1F3FA')).grid(row=0,column=1,rowspan=2,padx=18)
            actions=ctk.CTkFrame(card,fg_color='transparent'); actions.grid(row=2,column=1,padx=15,pady=12)
            fav=ctk.CTkButton(actions,text='♥' if o.url in favorites else '♡',width=34,fg_color=BORDER,command=lambda:None); fav.pack(side='left',padx=5); fav.configure(command=lambda o=o,b=fav:self.favorite(o,b))
            ctk.CTkButton(actions,text='Ver oferta ↗',width=105,fg_color=ACCENT,command=lambda o=o:self.open(o.url)).pack(side='left')
    def favorite(self,o,b):
        enabled=self.db.toggle(o); b.configure(text='♥' if enabled else '♡'); self.notify('Favorito salvo.' if enabled else 'Favorito removido.')
        if self.page=='favorites': self.show_offers(self.db.favorites())
    def open(self,url):
        if valid_url(url): webbrowser.open(url)
    def export(self,ext):
        if not self.visible: self.notify('Nenhuma oferta para exportar.'); return
        path=filedialog.asksaveasfilename(defaultextension='.'+ext,initialfile='PriceRadar-ofertas.'+ext,filetypes=[(ext.upper(),'*.'+ext)])
        if path:
            try: export_file(path,self.visible); self.notify('Exportação concluída: '+path)
            except Exception: logging.exception('Exportar'); messagebox.showerror('Exportação indisponível','Feche o arquivo se estiver aberto e verifique a permissão da pasta.')
    def report_callback_exception(self,exc,value,tb):
        logging.error('Interface',exc_info=(exc,value,tb)); messagebox.showerror('PriceRadar BR','Não foi possível concluir a ação. Tente novamente. Os detalhes estão no log local.')
    def close(self):
        self.cancel.set()
        if self.busy:
            self.notify('Fechando o navegador antes de sair…'); self.after(200,self.close); return
        self.closed=True; self.destroy()

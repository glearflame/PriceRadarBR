# PriceRadar BR

Aplicativo desktop Python de comparação de ofertas do Mercado Livre, Amazon Brasil e Shopee.

## Estado desta entrega

**Este pacote contém o projeto fonte; não contém um EXE Windows compilado.** Foi produzido e verificado em Linux. PyInstaller não compila executáveis Windows em Linux. O script e o workflow abaixo realizam a compilação em Windows. O workflow foi fornecido, mas não foi executado nesta entrega.

Implementado: interface CustomTkinter escura/clara, navegação lateral, cards ordenados por preço, destaque do menor preço coletado, busca textual e extração do título por link, Selenium + undetected-chromedriver + BeautifulSoup, consulta em thread, progresso animado, hover, cancelamento cooperativo, histórico local limitado a 100 buscas, favoritos, filtros por loja, exportação Excel/PDF, atalhos, logs rotativos e empacotamento Windows.

A interface usa microinterações nativas e barra de progresso indeterminada; não inclui animações complexas de transição. Pillow gera a marca da interface. Não há servidor, autenticação do aplicativo nem telemetria.

**Validação feita:** cinco testes automatizados de valores monetários, domínios, persistência, parsers com HTML sintético e exportações; importação das dependências; compilação sintática; inspeção visual do PDF de teste.
**Não validado:** renderização gráfica do aplicativo (sem servidor gráfico disponível), coleta real nas lojas, execução Windows e EXE. Os seletores são adaptadores iniciais e podem precisar de ajuste nas páginas atuais. Não considere esta versão homologada para produção sem esses testes.

## Gerar o EXE em Windows — caminho mais simples

1. Instale Python **3.11 de 64 bits**, incluindo o Python Launcher (`py`), de https://www.python.org/downloads/windows/.
2. Instale Google Chrome. Ele é necessário para consultas, também na versão empacotada.
3. Extraia este ZIP para uma pasta gravável, por exemplo `C:\PriceRadarBR`.
4. Abra a pasta e execute `build_windows.bat` com dois cliques.
5. Aguarde a instalação, os testes e a compilação; a internet é necessária.
6. O aplicativo estará em `dist\PriceRadarBR\PriceRadarBR.exe`.
7. O pacote para compartilhar estará em `dist\PriceRadarBR-Windows.zip`.

**Mantenha toda a pasta junto do EXE**, incluindo `_internal`. Não envie apenas o executável. Usamos `--onedir` para empacotar os recursos do CustomTkinter de forma explícita. O usuário final não precisa instalar Python; precisa de Chrome e internet. O driver é baixado na primeira consulta, podendo exigir permissão de escrita e acesso à rede.

### Comando exato configurado no script e no workflow

```bat
python -m PyInstaller --noconfirm --clean --onedir --windowed --name PriceRadarBR --collect-all customtkinter --collect-all undetected_chromedriver --collect-all reportlab --hidden-import PIL._tkinter_finder main.py
```

No `.bat`, `python` é chamado por `.venv\Scripts\python`. Esse comando **não foi executado para Windows neste ambiente Linux**.

### Compilação manual

```bat
py -3.11 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python main.py
python -m PyInstaller --noconfirm --clean --onedir --windowed --name PriceRadarBR --collect-all customtkinter --collect-all undetected_chromedriver --collect-all reportlab --hidden-import PIL._tkinter_finder main.py
```

## Gerar e baixar pelo GitHub, sem compilar no seu computador

1. Crie um repositório e envie o **conteúdo** desta pasta na raiz, incluindo `.github/workflows/windows.yml`.
2. No GitHub, vá em **Actions → Build Windows → Run workflow**.
3. Aguarde o resultado. O workflow testa o código, gera o executável em Windows e testa as importações do EXE.
4. Na execução concluída, baixe **Artifacts → PriceRadarBR-Windows**.
5. Extraia todos os arquivos antes de executar `PriceRadarBR.exe`.
6. Para download público, crie uma **Release** no repositório e anexe o ZIP validado. Compartilhe a página da release.

O teste de importação não substitui o teste funcional com Chrome. Nenhum repositório foi criado nem arquivo publicado automaticamente nesta entrega.

## Uso

- Busque por marca + modelo; termos genéricos misturam produtos.
- Cole um link HTTPS completo de uma das três lojas para extrair o título. Links encurtados não são aceitos.
- O Chrome abre em janela separada e não utiliza sua sessão pessoal. As três lojas são consultadas sequencialmente, com tempo de espera limitado por página.
- Os resultados aparecem conforme cada loja termina. Uma falha não descarta as ofertas já coletadas.
- **Menor preço coletado** significa o menor valor entre os anúncios visíveis, não a garantia de menor preço do mercado nem equivalência exata do produto.
- Confira modelo, tamanho, voltagem, condição, vendedor, frete e cupons na loja antes de comprar. O filtro textual é heurístico e pode incluir acessórios ou variantes.
- Favoritos guardam o preço no momento da coleta. Histórico e favoritos não são atualizados em segundo plano; faça nova busca.
- Excel/PDF exportam as ofertas da visualização atual, respeitando filtro e ordem.
- `Ctrl+K`: foco na busca. `Enter`: buscar/cancelar. `Esc`: cancelar. `Ctrl+E`: exportar Excel.
- Cancelar e fechar aguardam a operação de navegador atual terminar. Inicialização/download do driver dependem da biblioteca externa e podem demorar.

## Dados e diagnóstico

Windows: `%LOCALAPPDATA%\PriceRadarBR\radar.sqlite3` e `app.log` (até três arquivos de aproximadamente 1 MB).
Linux: `~/.local/share/PriceRadarBR/`.

Faça backup do banco com o aplicativo fechado. Não há coleta de credenciais. Logs podem conter detalhes de URLs consultadas: revise antes de compartilhar.

Se ChromeDriver informar versão incompatível, abra `chrome://version` no Chrome, copie o número principal e configure-o em **Configurações**. Deixar em branco usa a seleção automática da biblioteca.

Shopee e outras lojas podem pedir login, CAPTCHA ou bloquear automação. O programa não resolve CAPTCHA nem contorna autenticação. Ele informa indisponibilidade; não preenche resultados com dados fictícios. Uma coleta vazia também pode indicar mudança de seletores, que ficam em `priceradar/scraper.py`.

## Arquitetura e manutenção

- `main.py`: inicialização, log e entrada compatível com congelamento.
- `priceradar/app.py`: interface; eventos da thread chegam à UI por fila.
- `priceradar/scraper.py`: navegador, adaptadores HTML e relevância textual.
- `priceradar/core.py`: modelo, centavos inteiros, URLs e SQLite.
- `priceradar/exporters.py`: exportações com escrita temporária e troca atômica.
- `tests/test_core.py`: testes offline reproduzíveis.
- `requirements.txt`: dependências com faixas limitadas. `DEPENDENCIES.txt` no pacote compilado registra versões exatas usadas naquele build.

Antes de distribuir comercialmente, teste o pacote em Windows limpo nas três lojas e reveja as licenças dos componentes incluídos; undetected-chromedriver é distribuído sob GPL-3.0. A assinatura digital do executável exige certificado próprio e não está incluída.

## Referências

- https://www.pyinstaller.org/ — compilar no sistema operacional de destino.
- https://customtkinter.tomschimansky.com/documentation/packaging/ — recursos e empacotamento CustomTkinter.
- https://github.com/ultrafunkamsterdam/undetected-chromedriver — instalação, dependências e limitações do navegador.

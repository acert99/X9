# Presence Agent

> **Aviso**: este projeto foi feito por um entusiasta, nao um
> desenvolvedor profissional, com ajuda de IA. Funciona no meu uso
> pessoal, mas nao passou por revisao de seguranca formal nem por
> desenvolvedores experientes. Use por sua conta e risco, revise o
> codigo antes de confiar nele para algo sensivel, e sinta-se a
> vontade para abrir issues ou PRs com correcoes.

Agente local de monitoramento de presenca por webcam, acionado
manualmente. Voce abre o programa antes de uma sessao remota (por
exemplo via AnyDesk) e fecha ao final. Enquanto estiver ativo, ele
detecta se existe uma pessoa fisicamente em frente ao computador e
envia uma notificacao para o celular.

O agente nao conhece o AnyDesk nem qualquer outro software de acesso
remoto. Ele so sabe monitorar enquanto estiver ligado. Quem decide
quando iniciar e quando parar e o operador.

## Aviso importante

* A webcam so e aberta quando o operador clica em "Iniciar
  monitoramento" na bandeja. Nao existe nenhum modo automatico ou
  oculto de acionamento.
* Nenhuma imagem ou video e salvo em disco. Cada frame e processado
  pelo detector em memoria e descartado logo em seguida. So o
  resultado (pessoa detectada ou nao, com que confianca) e usado.
* Encerrar o programa libera a webcam imediatamente.

## Para quem so vai usar o programa

Se voce recebeu um `PresenceAgentSetup.exe` ou um `PresenceAgent.exe`
pronto, nao precisa instalar Python nem editar nada a mao:

1. Rode o instalador (`PresenceAgentSetup.exe`) e siga o assistente,
   ou copie o `PresenceAgent.exe` para onde quiser se for a versao
   sem instalador.
2. Na primeira vez que abrir, uma janela pequena vai pedir a URL de
   notificacao. Cole algo como `ntfy://ntfy.sh/um_nome_dificil_de_adivinhar`
   e clique em Concluir. Instale o app ntfy no celular e inscreva no
   mesmo topico para receber os alertas.
3. Pronto. O icone fica na bandeja com o menu de iniciar e parar o
   monitoramento. Isso so acontece uma vez, nas proximas aberturas o
   programa ja usa a configuracao salva.

Nada disso precisa de internet depois de instalado, exceto para
enviar as proprias notificacoes.

## Como funciona por dentro

```
Usuario inicia pela bandeja
        |
Webcam e aberta
        |
Detector roda a cada frame (YOLOX Nano)
        |
Pessoa confirmada por alguns segundos seguidos?
        |
     sim -> notificacao no celular -> cooldown
        |
Continua monitorando ate o usuario parar
```

Cada modulo em `src/` faz uma unica coisa e nao conhece os outros:

| Modulo               | Responsabilidade                                    |
|-----------------------|------------------------------------------------------|
| `camera.py`           | Abrir, ler e liberar a webcam                        |
| `detector.py`         | Rodar o YOLOX Nano e dizer se tem pessoa no frame     |
| `temporal_filter.py`  | Confirmar presenca so apos varios frames positivos    |
| `notifier.py`         | Enviar notificacao via Apprise com cooldown           |
| `tray.py`             | Icone e menu na bandeja do Windows                   |
| `config.py`           | Carregar e validar o config.yaml                     |
| `paths.py`            | Resolver caminhos em modo script e em modo executavel |
| `setup_wizard.py`     | Janela de configuracao inicial (so aparece uma vez)   |
| `main.py`             | Orquestrar todos os modulos acima                    |

Em modo executavel, o `config.yaml` e o log ficam numa pasta propria
do usuario (`%LOCALAPPDATA%\PresenceAgent`), separada de onde o
programa foi instalado. Isso evita precisar de permissao de
administrador so para gravar a configuracao.

## Para quem vai gerar o executavel ou o instalador

Essa parte e feita uma vez, numa maquina Windows com Python
instalado, para produzir o `.exe` (ou o instalador completo) que
depois vai ser distribuido para quem so vai usar o programa.

### Caminho mais simples: um clique so

Na raiz do projeto tem o arquivo `INSTALAR.bat`. Clique duas vezes
nele. Ele confere se o Python esta instalado, prepara o ambiente,
baixa o modelo, gera o executavel e, se o Inno Setup ja estiver
instalado, gera tambem o instalador completo, tudo numa tacada so.

Se o Python ainda nao estiver instalado, o script avisa e te
direciona para https://www.python.org/downloads/ (lembre de marcar
"Add python.exe to PATH" durante a instalacao). Se o Inno Setup ainda
nao estiver instalado, o script gera o `.exe` normalmente e avisa que
falta so esse passo para o instalador completo.

O resultado final fica em `dist_installer\PresenceAgentSetup.exe`
(ou em `dist\PresenceAgent.exe`, se o Inno Setup ainda nao tiver sido
instalado).

### Caminho passo a passo, se preferir rodar cada etapa manualmente

#### 1. Instalar dependencias e rodar direto do codigo (opcional, para testar)

Requer Python 3.12 no Windows.

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python scripts\download_model.py
copy config.yaml.example config.yaml
```

Edite o `config.yaml` recem criado com a URL de notificacao real, e
rode:

```powershell
python src\main.py
```

Rodando assim (sem ser executavel), o `config.yaml` fica na raiz do
projeto e e lido dali, do jeito tradicional.

O `download_model.py` baixa o YOLOX Nano oficial (Apache 2.0, Megvii
BaseDetection) direto do release no GitHub. Esse mesmo arquivo foi
validado durante o desenvolvimento contra imagens reais, retornando
corretamente pessoa detectada com confianca 0.87 numa foto com duas
pessoas e nenhuma deteccao numa foto sem gente.

Para validar a instalacao sem depender da webcam:

```powershell
python scripts\check_detection.py caminho\para\foto.jpg
```

### 2. Gerar o executavel

```powershell
scripts\build_exe.bat
```

Esse script cria o ambiente virtual se nao existir, instala tudo,
baixa o modelo se faltar, e roda o PyInstaller com o modelo ja
embutido dentro do `.exe`. O resultado fica em
`dist\PresenceAgent.exe`. Diferente da versao anterior deste projeto,
esse executavel nao precisa mais de um `config.yaml` pronto de
antemao: ele mesmo pergunta a URL de notificacao na primeira
execucao, atraves do `setup_wizard.py`.

### 3. Gerar o instalador de verdade (recomendado para distribuir)

Instale o Inno Setup (gratuito): https://jrsoftware.org/isdl.php

Depois rode:

```powershell
scripts\build_installer.bat
```

Isso compila `scripts\PresenceAgent.iss` e gera
`dist_installer\PresenceAgentSetup.exe`, um instalador com tela de
boas vindas, escolha de pasta, atalho no menu iniciar, atalho
opcional na area de trabalho, opcao de iniciar junto com o Windows,
e desinstalador registrado no Windows.

Esse `PresenceAgentSetup.exe` e o arquivo unico que voce compartilha
com quem so vai usar o programa. Basta rodar e seguir o assistente.

Nem o build do `.exe` nem o do instalador foram testados numa maquina
Windows real durante o desenvolvimento deste projeto, ja que ele foi
feito em ambiente Linux. A sintaxe de ambos os scripts segue as
praticas padrao do PyInstaller e do Inno Setup. Se o executavel
reclamar de algum modulo faltando ao abrir, o mais comum e precisar
adicionar mais uma flag `--hidden-import` em `build_exe.bat` para o
modulo citado no erro.

## Testes automatizados

```powershell
pip install pytest
pytest tests/ -v
```

Os testes cobrem o filtro temporal, a validacao do config.yaml, a
geracao do config pelo assistente inicial, e a resolucao de caminhos
em modo script e em modo executavel simulado. Nao dependem de webcam,
rede, nem de uma janela grafica sendo exibida de verdade.

## Roadmap

* MVP (este projeto): webcam, deteccao, notificacao, cooldown, bandeja, instalador
* v1.1: screenshot opcional no alerta, logs estruturados (ja parcialmente coberto pelo RotatingFileHandler em `main.py`)
* v1.2: multiplas webcams, multiplos canais simultaneos, estatisticas
* v2: reconhecimento de pessoas autorizadas, modelos intercambiaveis, plugins

## Integracao continua

Cada push ou pull request na branch `main` roda automaticamente a
suite de testes via GitHub Actions (`.github/workflows/tests.yml`).
Os testes nao dependem de webcam, modelo baixado ou ambiente grafico,
entao rodam limpos em qualquer runner do Actions.

## Licenca

Este codigo esta sob licenca MIT, veja o arquivo `LICENSE`.

## Creditos

Este projeto so existe por causa do trabalho de terceiros, todo ele
open source. Credito e agradecimento a cada um:

| Projeto | Uso neste agente | Licenca |
|---|---|---|
| [YOLOX](https://github.com/Megvii-BaseDetection/YOLOX) (Megvii BaseDetection) | Modelo de deteccao (YOLOX Nano, ONNX) usado em `detector.py` | Apache 2.0 |
| [OpenCV](https://opencv.org/) (`opencv-python-headless`) | Captura da webcam e pre-processamento de frames | Apache 2.0 |
| [ONNX Runtime](https://onnxruntime.ai/) | Motor de inferencia do modelo em `detector.py` | MIT |
| [Apprise](https://github.com/caronc/apprise) | Camada de notificacao (ntfy, Telegram, Gotify, Discord, email etc.) em `notifier.py` | BSD 2-Clause |
| [ntfy](https://ntfy.sh/) | Servico/app de push recomendado para receber os alertas no celular | Apache 2.0 |
| [pystray](https://github.com/moses-palmer/pystray) | Icone e menu na bandeja do Windows em `tray.py` | LGPL-3.0-or-later / GPL-3.0-or-later |
| [Pillow](https://python-pillow.org/) | Geracao do icone da bandeja | MIT-CMU (licenca estilo Pillow/HPND) |
| [PyYAML](https://pyyaml.org/) | Leitura do `config.yaml` em `config.py` | MIT |
| [NumPy](https://numpy.org/) | Manipulacao de arrays de imagem no pre/pos-processamento do detector | BSD 3-Clause |
| [PyInstaller](https://pyinstaller.org/) | Empacotamento do `.exe` (`scripts/build_exe.bat`) | GPL-2.0-or-later (com excecao de bootloader, nao afeta o codigo aqui gerado) |
| [Inno Setup](https://jrsoftware.org/isinfo.php) | Geracao do instalador (`scripts/build_installer.bat`) | Freeware (nao redistribui codigo deste projeto) |

Se algum credito estiver faltando ou incorreto, abra uma issue ou PR
corrigindo.

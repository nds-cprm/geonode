# Relatório: imagem base multi-stage unificada do GeoNode (Ubuntu 24.04 e 26.04)

Data: 22/11/2026. Artefato: `docker/base/ubuntu/multi-stage/`, com um `Dockerfile` único e os diretórios `24/` e `26/`.

Este relatório consolida os testes das duas imagens base multi-stage:
- a de Ubuntu 24.04, para o GeoNode 5.0.x;
- a de Ubuntu 26.04, para o GeoNode master.

Ele também traz os resultados do build da versão unificada.

## 1. Resumo

**Suíte de testes do GeoNode** (grupos e comandos da CI do GeoNode, sobre uma imagem do GeoNode construída em cima das imagens `release` arm64 do build unificado, em 22/11/2026):

| Base | GeoNode | Testes | Resultado | Duração |
|---|---|---|---|---|
| `ubuntu-24.04-pg15` | 5.0.x (`b7e73644a`) | 1.527 | ✅ os 7 grupos passaram, sem falhas (2 ignorados) | 2 h 43 min |
| `ubuntu-26.04-pg18` | master (`d74ea0392`) | 2.046 | 1 erro de ambiente (`test_map_default_thumb`), 2 ignorados; os outros 6 grupos passaram integralmente | 2 h 45 min |

Os resultados são os mesmos das rodadas anteriores, feitas com os Dockerfiles por versão antes da retirada dos bindings Python do GDAL do sistema (seção 7): a retirada não afetou nenhum teste.

**Imagens `release` (arm64), comparadas com as bases oficiais (amd64):**

| | Base oficial 24.04 | Proposta 24.04 | Base oficial 26.04 | Proposta 26.04 |
|---|---|---|---|---|
| Tamanho | 1,44 GB | **570 MB** | 1,66 GB | **666 MB** |
| Compiladores | sim | **não** | sim | **não** |
| CVEs (críticos / altos) | 3.475 (42 / 760) | **111 (0 / 2)** | 3.772 (43 / 794) | **97 (0 / 2)** |

**Build unificado** (amd64 e arm64, `release` e `devel`, 24.04 e 26.04): as quatro tags foram construídas como manifest lists das 11:14 às 12:56. O smoke test passou nas oito imagens, no fim do build e de novo em cada arquitetura puxada da manifest list. As imagens arm64 têm os mesmos pacotes e os mesmos CVEs das imagens por versão (seção 8).

**Conclusão.** As bases multi-stage atendem o GeoNode 5.0.x (24.04) e o GeoNode master (26.04). A imagem final não tem compiladores, ocupa menos da metade das oficiais e não tem CVE crítico nem alto nos pacotes do SO. O Dockerfile unificado produz as duas versões com os mesmos passos dos Dockerfiles por versão, e cada imagem se verifica com um smoke test no fim do build.

**Problemas das bases oficiais corrigidos no build unificado** (seção 10): compiladores e ferramentas de empacotamento Debian na imagem de produção, falta de `apt-get upgrade` (22 e 27 pacotes com correção pendente), pacotes recomendados instalados, bindings do GDAL sem `gdal_array`, pacotes Python do sistema duplicando o venv, pacotes do GeoNode recompilados no build dele, cliente PostgreSQL 15 fixo (na 26.04, do PGDG do 24.04), `apt-key`, limpeza de camadas sem efeito, só amd64, nenhuma verificação da imagem e dois Dockerfiles divergentes.

**Pendências:**
- rodar a suíte em amd64; até agora, só o smoke test rodou nessa arquitetura.

## 2. Ambiente de execução

Todos os builds e testes deste relatório rodaram com **Podman no macOS, em arm64**, numa única máquina. Não houve Docker nem CI do GitHub.

| Item | Valor |
|---|---|
| Hospedeiro | Mac com Apple M4 Pro (arm64), 14 núcleos, 48 GB de RAM, macOS 27.2.1 |
| Motor de containers | Podman 6.1.4, sem o CLI `docker` |
| Máquina virtual do Podman | `podman-machine-default`, VM libkrun com Fedora 44 (kernel 7.2.7, aarch64), 7 CPUs, 28 GB de RAM e 93 GB de disco |
| Compose | docker-compose 5.6.0, apontado para o socket do Podman (`DOCKER_HOST`) |
| Imagens construídas em arm64 | nativas |
| Imagens construídas em amd64 (build unificado) e serviços só amd64 da CI | emuladas com `qemu-x86_64-static` (binfmt_misc da VM) |
| Varredura de vulnerabilidades | Trivy 0.76.2, num container, lendo as imagens pelo socket do Podman |

**Consequências da emulação:**
- os tempos dos grupos e a corrida de boot vista no `security` (seção 4.3; no `csw`, nas rodadas anteriores) refletem a emulação dos serviços amd64, e não valem como referência de desempenho;
- os builds amd64 também são emulados, bem mais lentos que os nativos.

## 3. O artefato

| Arquivo | Papel |
|---|---|
| `Dockerfile` | build multi-stage único (`build` → `runtime` → `devel`/`release`) |
| `smoke-test` | verificação da imagem, rodada no fim do `runtime` e do `devel` e instalada como `geonode-base-smoke-test` |
| `get-runtime-packages` | lista os pacotes do Ubuntu que fornecem as bibliotecas dos binários do venv (`ldd` + `dpkg -S`); roda no estágio `build`, e o `runtime` instala a lista; `--help` mostra o uso |
| `24/requirements.txt`, `26/requirements.txt` | pacotes Python compilados no venv para cada versão |
| `geonode-tests` | roda a suíte de testes da CI do GeoNode sobre uma imagem do GeoNode construída em cima da base (seção 4.4) |

O que muda de uma versão para outra vem de build args, com padrões do Ubuntu 26.04:

| Build arg | Padrão (26.04) | 24.04 |
|---|---|---|
| `UBUNTU_RELEASE` | `26` | `24` |
| `UBUNTU_IMAGE_TAG` | `<UBUNTU_RELEASE>.04` | `24.04` (padrão) |
| `EXTRA_BUILD_PACKAGES` | `libopenblas-dev libcrypt-dev` | `libmemcached-dev` |
| `POSTGRESQL_CLIENT_VERSION` | `18` | `15` |

**Verificações do próprio build:**
- **Versão do Ubuntu:** o primeiro `RUN` falha se a imagem `ubuntu:${UBUNTU_IMAGE_TAG}` não for da versão `UBUNTU_RELEASE`.
- **`EXTRA_BUILD_PACKAGES` vazio:** só gera um aviso.
- **`POSTGRESQL_CLIENT_VERSION`:** o build falha se ele vier vazio ou não for número.

**Pacotes compilados no venv** (os do GeoNode sem wheel para o Python de cada versão):

| Pacote | 24.04 (GeoNode 5.0.x, Python 3.12) | 26.04 (GeoNode master, Python 3.14) |
|---|---|---|
| GDAL (versão do `gdal-config`) | 3.8.4 | 3.12.2 |
| numpy | 1.26.* (para o `gdal_array`) | 1.26.4, sem wheel para Python 3.14 |
| psycopg2 | 2.9.12 | 2.9.13 |
| uWSGI | 2.0.30 | 2.0.30 |
| pylibmc | 1.6.3 | não entra (a master o removeu) |
| psutil | 5.9.8 (sem wheel em arm64) | não entra (tem wheel) |
| invoke, sherlock | 2.2.0, 0.4.1 | 2.2.0, 0.4.1 |

## 4. Suíte de testes do GeoNode

### 4.1 Como foi rodada

O script `docker/base/ubuntu/multi-stage/geonode-tests` (seção 4.4) segue o `.github/workflows/tests.yml` e o `run-test-suite.yml` da própria ref testada:
1. exporta o código com `git archive`;
2. constrói a imagem do GeoNode do `Dockerfile` da raiz, só com o `FROM` trocado pela base;
3. para cada grupo da CI, sobe uma stack nova, cria os bancos de teste, roda o `test_command` no container django, grava os logs e derruba a stack com os volumes.

**Diferenças em relação à CI, todas de propósito:**
- sem `--failfast`;
- sem portas publicadas;
- sem envio ao Codecov;
- imagens que só existem para outra arquitetura rodam emuladas.

**Serviços de apoio:** as imagens da CI (`geonode/postgis:15-3.5-latest`, `geonode/geoserver`, `geonode/nginx` e, na 5.0.x, `geonode/geoserver_data`), todas só em amd64, rodaram emuladas.

### 4.2 Resultados

Imagens testadas: `docker.io/ndscprm/geonode-base:ubuntu-24.04-pg15` e `ubuntu-26.04-pg18`, construídas do Dockerfile unificado, em linux/arm64. Logs em `~/.cache/geonode-base-tests/logs/20261122-130311` (5.0.x), `20261122-161925` (master) e `20261122-190007` (segunda tentativa do `security` da master). O `pip check` saiu limpo nas duas imagens do GeoNode.

**Ubuntu 24.04, GeoNode 5.0.x** (`b7e73644a`, Django 5.2.16, Pillow 12.1.1):

| Grupo | Testes | Resultado | Tempo |
|---|---|---|---|
| smoke | 48 | ✅ OK | 15 min |
| main | 770 | ✅ OK (1 ignorado) | 32 min |
| security | 81 | ✅ OK | 17 min |
| gis_backend | 37 | ✅ OK | 15 min |
| rest_apis | 233 | ✅ OK | 23 min |
| csw | 12 | ✅ OK | 14 min |
| upload | 346 | ✅ OK (1 ignorado) | 47 min |
| **Total** | **1.527** | **✅ sem falhas** | 2 h 43 min |

**Ubuntu 26.04, GeoNode master** (`d74ea0392`, `5.2.0.dev0`, Django 5.2.19, Pillow 13.0.0):

| Grupo | Testes | Resultado | Tempo |
|---|---|---|---|
| smoke | 60 | ✅ OK | 15 min |
| main | 1.075 | 1 erro (`test_map_default_thumb`), 1 ignorado | 38 min |
| security | 113 | ✅ OK (na segunda tentativa) | 16 min |
| gis_backend | 47 | ✅ OK | 14 min |
| rest_apis | 265 | ✅ OK | 24 min |
| csw | 12 | ✅ OK | 14 min |
| upload | 474 | ✅ OK (1 ignorado) | 44 min |
| **Total** | **2.046** | **1 erro** | 2 h 45 min |

O tempo de cada grupo inclui a subida de uma stack nova (cerca de 3 minutos) e a carga das camadas do gisdata (cerca de 10 minutos).

### 4.3 Ocorrências

- **`test_map_default_thumb` (26.04, grupo `main`): erro de ambiente.** O teste gera a miniatura de um mapa com fundo da Wikimedia e a baixa por `http://localhost:8000/uploaded/...`. Dois fatores o derrubam, e nenhum depende da imagem base:
  - os tiles da Wikimedia respondem 403 no ambiente de testes;
  - com `DEBUG=False`, o uWSGI não serve `/uploaded/`, e o teste recebe uma página 404 no lugar da imagem.

  Na 5.0.x o mesmo teste passa, porque lá a miniatura nem chega a ser gerada sem o fundo.
- **`security` (26.04): a stack não subiu na primeira tentativa.** O PostgreSQL da imagem `geonode/postgis` (emulada) inicializa o banco, desliga e sobe de novo. O healthcheck deu o serviço como pronto antes dessa reinicialização, e o django tentou conectar no intervalo: `connection to server at "db" ... failed: Connection refused`, e o container saiu. Nenhum teste chegou a rodar. Na segunda tentativa, os 113 testes passaram. Nas rodadas com os Dockerfiles por versão, a mesma corrida atingiu o grupo `csw`. Não depende da imagem base.

### 4.4 O script `geonode-tests`

**Onde fica.** `docker/base/ubuntu/multi-stage/geonode-tests`, ao lado do Dockerfile unificado. O script acha a raiz do repositório pelo git (`git rev-parse --show-toplevel`), então pode ser chamado de qualquer diretório. O README tem a seção "Testing a base image", com as opções e as variáveis de ambiente.

**Para que serve.** Roda a suíte de testes do GeoNode sobre uma imagem do GeoNode construída em cima da base em teste, sem nenhum projeto derivado no meio. Uma falha aponta para a base ou para o código do GeoNode, e não para personalizações.

**Como reproduz a CI.** Lê da própria ref testada o `.github/workflows/tests.yml` (os grupos e os `test_command`) e o `run-test-suite.yml` (arquivo compose, arquivo de ambiente e argumentos do `up`). Não há lista fixa de grupos: a 5.0.x roda com o compose da 5.0.x, e a master com o da master.
- **Na 5.0.x:** `docker compose --env-file .env_test -f docker-compose-test.yml up -d`.
- **Na master:** `COMPOSE_ENV_FILES=.env_test docker compose up -d --no-deps db geoserver django nginx`.

A leitura do YAML usa o PyYAML da própria imagem do GeoNode, para não exigir Python com PyYAML no host.

**Uso:**

```bash
./docker/base/ubuntu/multi-stage/geonode-tests --ref master --base docker.io/ndscprm/geonode-base:ubuntu-26.04-pg18
./docker/base/ubuntu/multi-stage/geonode-tests --ref 5.0.x --base docker.io/ndscprm/geonode-base:ubuntu-24.04-pg15
./docker/base/ubuntu/multi-stage/geonode-tests --no-build --keep --ref master --base <base> csw   # um grupo, mantendo a stack
./docker/base/ubuntu/multi-stage/geonode-tests --down                                           # remove a stack mantida
```

**Opções principais:**
- **`--base`:** o padrão passou a ser `docker.io/ndscprm/geonode-base:ubuntu-26.04-pg18`, já com a nomenclatura nova de tags.
- **`--ref`:** precisa casar com a base, porque o GeoNode fixa o GDAL no `libgdal` dela: 5.0.x com a 24.04, master com a 26.04.
- **Outras:** `--platform`, `--service-image S=IMG`, `--no-build`, `-f`/`--failfast`, `-k`/`--keep`, `--down` e `-l`/`--list`.
- **Variáveis de ambiente:** `CONTAINER_ENGINE`, `BOOT_TIMEOUT` (padrão 3600 s), `MAX_FAILED_LIST` e `GEONODE_TESTS_DIR`.

**Logs:** ficam em `~/.cache/geonode-base-tests/logs/<data-hora>/`:
- `build.log`, `plan.json`, `override.yml` e `summary.txt`;
- por grupo, o log dos testes, o da subida da stack e o dos serviços. O dos serviços é gravado também quando a stack não sobe.

A saída é 0 só se todos os grupos passarem.

**Correções feitas no script durante as rodadas.** Nenhuma envolvia as imagens base.
- **Plataforma das imagens dos serviços.** O `podman pull --platform linux/arm64` termina com sucesso mesmo quando a imagem só existe em amd64, e baixa a amd64. Agora a plataforma é lida da imagem baixada antes de ir para o override.
- **Nome do container.** O compose usa `container_name: <serviço>4${COMPOSE_PROJECT_NAME}`, e o script procurava `django<projeto>`.
- **Registro do comando no log.** Um `echo` com aspas duplas expandia o `$TESTS` antes da hora e, com `set -u`, abortava os grupos `main`, `security` e `gis_backend` na primeira rodada da 5.0.x. O comando agora é gravado por um here-doc literal.
- **`COMPOSE_ENV_FILES`.** O compose da master usa `env_file: ${COMPOSE_ENV_FILES:-.env}`; o script passou a exportar a variável com o arquivo de ambiente da CI, como o workflow faz.
- **Logs na falha de subida.** Os logs dos serviços passaram a ser gravados também quando a stack não sobe.

**Pontos de atenção:**
- **O `--list` constrói a imagem do GeoNode,** ou a reaproveita com `--no-build`, porque o PyYAML vem dela. Não é uma consulta instantânea, e disputa a máquina com outros builds.
- **Duração.** Cerca de 2 h 45 min por linha do GeoNode neste ambiente. Cada grupo sobe uma stack nova (cerca de 3 min com os serviços emulados) e carrega o gisdata (cerca de 10 min).
- **Emulação.** Em arm64, os serviços da CI rodam emulados. Isso alonga o boot e pode expor corridas que não acontecem no nativo, como a do `security` (seção 4.3). O `--service-image` permite trocar por imagens nativas, ao custo de fugir das imagens exatas da CI.
- **Requisitos:** bash 4.3 ou mais novo (no macOS, o do Homebrew), git, e Docker ou Podman com compose.

## 5. Imagens

Dados coletados dentro de cada imagem; vulnerabilidades do Trivy 0.76.2 (`--scanners vuln`, cada CVE contado uma vez por imagem pela maior severidade). As bases oficiais só existem em amd64; as propostas foram medidas em arm64.

| | Oficial 24.04 | `release` 24.04 | `devel` 24.04 | Oficial 26.04 | `release` 26.04 | `devel` 26.04 |
|---|---|---|---|---|---|---|
| Tamanho | 1,44 GB | **570 MB** | 1,23 GB | 1,66 GB | **666 MB** | 1,43 GB |
| Pacotes `dpkg` | 697 | 241 | 393 | 749 | 246 | 432 |
| Pacotes `-dev` | 86 | 1 (`systemd-dev`) | 79 | 116 | **0** | 107 |
| Compiladores | gcc, g++, make | nenhum | gcc 13.3, g++, make | gcc, g++, make | nenhum | gcc 15.2, g++, make |
| `linux-libc-dev` | sim | ausente | sim | sim | ausente | sim |
| Binários setuid/setgid | 15 | 13 | 13 | 14 | 12 | 12 |
| GDAL (bindings com `gdal_array`) | 3.8.4, não | 3.8.4, sim | 3.8.4, sim | 3.12.2, não | 3.12.2, sim | 3.12.2, sim |
| Bindings Python do GDAL no sistema | sim | não | não | sim | não | não |
| Cliente PostgreSQL | 15 | 15 | 15 | 15 (PGDG do 24.04) | 18 | 18 |
| **CVEs únicos** | **3.475** | **111** | 538 | **3.772** | **97** | 241 |
| Críticos / altos | 42 / 760 | 0 / 2 | 3 / 91 | 43 / 794 | 0 / 2 | 3 / 29 |
| ...em pacotes do SO | 3.468 | 108 (C=0, H=0) | 536 (C=3, H=89) | 3.750 | 93 (C=0, H=0) | 238 (C=3, H=27) |
| ...em pacotes Python (e Go, no 26.04) | 11 | 6 (H=2) | 6 (H=2) | 26 | 7 (H=2) | 7 (H=2) |
| Pacotes do SO com correção pendente | 22 | 0 | 0 | 27 | 0 | 0 |

**Leitura:**
- **Pacotes do SO nas bases oficiais:** a maior parte dos CVEs vem do `linux-libc-dev` e dos `-dev` que acompanham os compiladores. As oficiais também têm pacotes com correção publicada e não aplicada, o que mostra que não recebem `apt-get upgrade`.
- **Pacotes do SO nas `release` propostas:** nenhum CVE crítico ou alto, e nenhum com correção publicada no Ubuntu.
- **CVEs corrigíveis que restam nas `release`:** estão nos bindings do GDAL (corrigidos no 3.13) e na cópia do `setuptools` embutida no pip. Na 26.04 há ainda um médio no Go do `/usr/bin/pebble`, que vem com a própria `ubuntu:26.04`.
- **`devel`:** é a `release` mais os compiladores e os `-dev`, e os CVEs a mais vêm desses pacotes (413 ocorrências no `linux-libc-dev` na 24.04 e 134 na 26.04). Por isso a imagem de produção deve ser a `release`.
- **Imagens finais do GeoNode:**
  - **5.0.x sobre a 24.04:** os pins do próprio GeoNode acrescentam CVEs, que a base não tem como resolver. Os críticos estão no Pillow 12.1.1 e no PyJWT 2.8.0.
  - **master sobre a 26.04:** a imagem final tem exatamente os mesmos 97 CVEs da base.

## 6. Smoke test

O `smoke-test` substitui as verificações fixas que cada Dockerfile por versão tinha no fim. Ele imprime `ok` ou `FAIL` por verificação, sai com 1 se alguma falhar, e confere:
- **pacotes do `requirements.txt`:** cada um instalado na versão do pin, com os módulos importando. Os nomes dos módulos vêm dos metadados do pacote; no uWSGI, o teste roda o binário e compara a versão;
- **GDAL:** bindings na versão do `libgdal`, `gdal_array` com numpy, PROJ funcionando (`EPSG:4326`), `ogr2ogr` e `gdal_translate` rodando;
- **PostgreSQL:** `psycopg2` ligado à `libpq`, e `pg_dump` com o major do build;
- **demais peças:** `libmagic`, `invoke`, `pip check`;
- **bindings do sistema:** nada de bindings Python do GDAL no sistema, nenhum `*.py` em `/usr/bin`, e o `gdal_calc.py` do `PATH` é o do venv. A opção `--no-system` pula esse grupo.

**Validação antes do build unificado.** O script foi rodado montado nas imagens dos Dockerfiles por versão, com os `requirements.txt` do diretório unificado:

| Imagem | Verificações | Resultado |
|---|---|---|
| `ubuntu24.04` (por versão) | 19 | ✅ todas passaram |
| `ubuntu26.04` (por versão) | 17 | ✅ todas passaram |
| `ubuntu24.04` com falhas forçadas (pin errado, pacote ausente, major do `pg_dump` errado, `/usr/bin/x.py`) | 5 falhas esperadas | ✅ as 5 detectadas, saída 1 |

**No build unificado.** O smoke test rodou no fim dos estágios `runtime` e `devel` de cada build. Depois, rodou de novo nas imagens prontas, puxando cada arquitetura da manifest list com `podman run --platform`; o `uname -m` confirmou a arquitetura certa em cada uma:

| Tag | amd64 | arm64 |
|---|---|---|
| `ubuntu-24.04-pg15` | ✅ 19/19 | ✅ 19/19 |
| `ubuntu-24.04-pg15-devel` | ✅ 19/19 | ✅ 19/19 |
| `ubuntu-26.04-pg18` | ✅ 17/17 | ✅ 17/17 |
| `ubuntu-26.04-pg18-devel` | ✅ 17/17 | ✅ 17/17 |

A 24.04 tem duas verificações a mais porque o `requirements.txt` dela também traz o pylibmc e o psutil.

## 7. Bindings Python do GDAL do sistema

A base não instala o `python3-gdal` nem o numpy do sistema. O GeoNode usa só os do venv. As primeiras rodadas da suíte foram feitas antes dessa mudança; a rodada sobre as imagens unificadas (seção 4) já foi feita sem eles, com os mesmos resultados.

**Como funciona:**
- **Pacote substituto local (placeholder).** O `gdal-bin` exige o `python3-gdal` numa versão exata. Um pacote vazio, gerado com `dpkg-deb`, declara `Provides` desses pacotes nas versões lidas do `apt-cache` no build. O apt continua íntegro (`apt-get check` limpo), e uma imagem derivada ainda pode instalar o `python3-gdal` real.
- **`/etc/dpkg/dpkg.cfg.d/geonode-no-system-gdal-scripts`.** Regras `path-exclude` impedem o dpkg de gravar os 18 utilitários Python do GDAL em `/usr/bin`. Eles vêm no próprio `gdal-bin` e quebrariam sem os bindings no Python do sistema. A regra vale também para atualizações futuras do `gdal-bin`.

**Efeito:**
- 2 pacotes a menos em cada `release`;
- 0 pacotes `-dev` na 26.04, que perdeu o `python3-numpy-dev`;
- um único numpy na imagem: na 26.04 havia dois, o 1.26.4 do venv e o 2.3.5 do sistema;
- 39 MB a 41 MB a menos;
- os mesmos CVEs, porque nenhum vinha dos pacotes retirados.

As alternativas descartadas, os efeitos em imagens derivadas e como reverter estão no README.

## 8. Build unificado (amd64 e arm64)

**Data:** 22/11/2026, das 11:14 às 12:56.

**Como:** `podman build --platform linux/amd64,linux/arm64 --manifest docker.io/ndscprm/geonode-base:<tag>`, com os comandos da seção 13. Cada tag é uma manifest list com as duas arquiteturas.

**Resultado:**

| Tag | Build | Pacotes `dpkg` (amd64 / arm64) | `-dev` | setuid/setgid | Tamanho da imagem (amd64 / arm64) |
|---|---|---|---|---|---|
| `ubuntu-24.04-pg15` | ✅ 11:14 → 11:45 | 241 / 241 | 1 | 13 | 546 MB / 570 MB |
| `ubuntu-24.04-pg15-devel` | ✅ 11:45 → 12:03 | 394 / 393 | 79 | 13 | 1,25 GB / 1,23 GB |
| `ubuntu-26.04-pg18` | ✅ 12:03 → 12:46 | 246 / 246 | 0 | 12 | 659 MB / 666 MB |
| `ubuntu-26.04-pg18-devel` | ✅ 12:46 → 12:56 | 433 / 432 | 107 | 12 | 1,47 GB / 1,43 GB |

O tamanho é o que o Podman reporta para a imagem de cada arquitetura da manifest list (`podman image inspect --format '{{.Size}}'`, em unidades decimais, como no `podman images`). A manifest list em si não tem tamanho: o `podman images` mostra 1,1 kB para a tag. Os valores da 24.04 são os das imagens do novo build (seção 8.2), e os da 26.04 não mudaram. A amd64 é maior na `devel` e na `release` 26.04, e menor na `release` 24.04.

**O que o build unificado confirmou:**
- **`ARG` que usa outro `ARG`:** `UBUNTU_IMAGE_TAG=${UBUNTU_RELEASE}.04` funciona no Podman (buildah).
- **`COPY ${UBUNTU_RELEASE}/requirements.txt`:** pega o arquivo da versão certa.
- **Verificação da versão do Ubuntu:** passou nas duas (`Base image: ubuntu:24.04 (Ubuntu 24.04.5 LTS)` e `ubuntu:26.04 (Ubuntu 26.04.1 LTS)`).
- **Valores padrão:** os da 26.04 bastaram para a 26.04, e os três `--build-arg` da 24.04 produziram a imagem da 24.04 (pylibmc, psutil e cliente 15).
- **Smoke test:** passou nas oito imagens, inclusive nas amd64, que nunca tinham sido construídas antes.

**Vulnerabilidades das imagens arm64** (Trivy 0.76.2, mesma contagem da seção 5): iguais às das imagens por versão.

| Tag | CVEs únicos | Críticos / altos / médios / baixos | Pacotes do SO | Pacotes Python (e Go) | Com correção | Pacotes do SO com correção pendente |
|---|---|---|---|---|---|---|
| `ubuntu-24.04-pg15` | 111 | 0 / 2 / 84 / 25 | 108 (C=0, H=0) | 6 | 6 | 0 |
| `ubuntu-24.04-pg15-devel` | 538 | 3 / 91 / 261 / 183 | 536 | 6 | 6 | 0 |
| `ubuntu-26.04-pg18` | 97 | 0 / 2 / 79 / 16 | 93 (C=0, H=0) | 7 | 7 | 0 |
| `ubuntu-26.04-pg18-devel` | 241 | 3 / 29 / 145 / 64 | 238 | 7 | 7 | 0 |

### 8.1 Tempo de build: arm64 nativo e amd64 emulado

O build foi feito com `podman build --platform linux/amd64,linux/arm64 --manifest ...` no Mac arm64. O Podman construiu uma arquitetura de cada vez: a amd64, emulada com QEMU, e a arm64, nativa. Nas `release` a amd64 veio primeiro; nas `devel`, a arm64. Os logs não registram horário por passo, então os tempos abaixo vêm da hora de criação das imagens de cada arquitetura e do momento em que cada etapa apareceu no log. São aproximados.

**Medidos (24.04):**

| Tag | O que o build faz | arm64 (nativo) | amd64 (emulado) | Razão |
|---|---|---|---|---|
| `ubuntu-24.04-pg15` (`release`) | compila psycopg2, pylibmc, uWSGI, psutil e os bindings do GDAL; monta o `runtime` | ~5 min | ~25 min | ~5× |
| `ubuntu-24.04-pg15-devel` | instala os compiladores e os `-dev` com o apt (o resto vem do cache) | ~5 min (11:45 → 11:50) | ~13 min (11:50 → 12:03) | ~2,5× |

**Leitura:**
- **Instalação de pacotes** (apt, dpkg): o amd64 emulado fica cerca de 2 a 3 vezes mais lento.
- **Compilação de C:** a diferença sobe para 5 vezes ou mais, porque cada instrução do compilador passa pelo QEMU.

**Medidos (26.04):**

| Tag | O que o build faz | arm64 (nativo) | amd64 (emulado) | Razão |
|---|---|---|---|---|
| `ubuntu-26.04-pg18` (`release`) | compila também o numpy 1.26 do zero (sem wheel para Python 3.14) | ~8 min (12:38 → 12:46) | ~35 min (12:03 → 12:38) | ~4,5× |
| `ubuntu-26.04-pg18-devel` | só os pacotes de compilação (o venv vem do cache) | ~5 min (12:46 → 12:51) | ~5 min (12:51 → 12:56) | ~1× |

A estimativa feita durante o build (45 a 90 minutos para a `release` em amd64) ficou acima do medido. A compilação emulada do numpy foi cerca de 4,5 vezes mais lenta que a nativa, a mesma ordem da 24.04. Na `devel` da 26.04, o amd64 levou o mesmo tempo que o arm64: a instalação dos pacotes de compilação pesou menos que na 24.04, provavelmente porque os pacotes já estavam no cache de download.

**Consequência para a publicação.** Construir cada arquitetura numa máquina nativa, por exemplo com os runners arm64 do GitHub Actions para o arm64 e os comuns para o amd64, e juntar as duas numa manifest list. Isso evita a emulação: pelos números da 24.04 `release`, o build multi-arquitetura cairia de cerca de 30 para cerca de 5 minutos por tag, e menos com cache.

### 8.2 Novo build com o `get-runtime-packages`

**Datas:** 22/11/2026, das 19:42 às 20:11, e 23/11/2026, das 06:58 às 07:03, com os mesmos comandos.

**O que mudou no Dockerfile:** a camada do estágio `build` que lista os pacotes de runtime (`find` + `ldd` + `dpkg -S` numa pipeline só) virou o script `get-runtime-packages`, com `--help`. O estágio o copia como `/usr/local/bin/geonode-base-get-runtime-packages` e roda `geonode-base-get-runtime-packages /usr/src/venv > /runtime-packages.txt`. O script fica só no `build`, fora das imagens finais.

**Verificação embutida.** A pipeline terminava com dois `grep -q` que exigiam `libgdal` e `libpq` na lista. Esses dois pacotes entram no `runtime` de qualquer jeito, como dependências do `gdal-bin` e do `postgresql-client`, então a verificação não protegia a imagem: só indicava, de forma indireta, que a detecção funcionava. Uma primeira versão do script a manteve como opção (`-r PREFIXO`). A versão final a trocou por uma regra genérica, sem parâmetro:
- as bibliotecas que ficam dentro do venv (embutidas nos wheels) são ignoradas;
- qualquer outra biblioteca sem pacote do Ubuntu faz o script falhar (saída 1), com a lista delas, porque a lista de pacotes sairia incompleta. Isso pega uma quebra do mapeamento `ldd` → `dpkg -S` ou uma biblioteca instalada fora do dpkg;
- uma lista vazia também é erro.

**Validação antes do build:**
- o script e a pipeline antiga rodaram dentro das imagens `devel` arm64 e produziram listas idênticas (99 pacotes na 24.04 e 112 na 26.04), sem nenhuma biblioteca sem pacote;
- uma cópia do `libpq.so.5` em `/opt/fora`, achada pelo `ldd` via `LD_LIBRARY_PATH`, fez o script sair com 1 e citar `/opt/fora/libpq.so.5`;
- os erros de uso saíram com 2.

**Resultado:**

| Tag | Build (22/11) | Pacotes de runtime (amd64 / arm64) | Smoke test (amd64 / arm64) |
|---|---|---|---|
| `ubuntu-24.04-pg15` | ✅ 19:42 → 20:01 | 99 / 99 | ✅ 19/19 / ✅ 19/19 |
| `ubuntu-24.04-pg15-devel` | ✅ 20:01 → 20:09 | (mesma lista) | ✅ 19/19 / ✅ 19/19 |
| `ubuntu-26.04-pg18` | ✅ 20:09 → 20:10 | 112 / 112 | ✅ 17/17 / ✅ 17/17 |
| `ubuntu-26.04-pg18-devel` | ✅ 20:10 → 20:11 | (mesma lista) | ✅ 17/17 / ✅ 17/17 |

O build de 23/11, com a versão final do script, levou de 1 a 2 minutos por tag. Ele rodou de novo só os dois passos do script, gerou as mesmas listas e reaproveitou o resto do cache. As imagens finais têm os mesmos IDs e digests das de 22/11. O smoke test foi rodado de novo depois de cada build, em cada arquitetura puxada da manifest list (o `uname -m` confirmou a arquitetura).

**Uso do cache no build de 22/11:**
- **24.04:** o estágio `build` não aproveitou o cache e foi refeito por inteiro, inclusive a compilação do venv. A causa provável é a limpeza das imagens antigas, que removeu as camadas intermediárias. O `runtime` e a `devel` também foram refeitos, e o smoke test rodou no fim de cada um.
- **26.04:** só os dois passos novos rodaram. Como a lista gerada foi idêntica, o Podman reaproveitou todo o estágio `runtime`, e as imagens ficaram iguais às anteriores.

**Imagens 24.04 refeitas, medidas de novo:**

| Imagem | Tamanho (`podman image`) | CVEs únicos | Críticos / altos / médios / baixos | Pacotes do SO | Pacotes Python | Pacotes do SO com correção pendente |
|---|---|---|---|---|---|---|
| `ubuntu-24.04-pg15` amd64 | 546 MB | 111 | 0 / 2 / 84 / 25 | 108 (C=0, H=0) | 6 | 0 |
| `ubuntu-24.04-pg15` arm64 | 570 MB | 111 | 0 / 2 / 84 / 25 | 108 (C=0, H=0) | 6 | 0 |
| `ubuntu-24.04-pg15-devel` amd64 | 1,25 GB | 538 | 3 / 91 / 261 / 183 | 536 | 6 | 0 |
| `ubuntu-24.04-pg15-devel` arm64 | 1,23 GB | 538 | 3 / 91 / 261 / 183 | 536 | 6 | 0 |

Os CVEs vêm do Trivy 0.76.2, com a mesma contagem da seção 5, e são idênticos aos do primeiro build unificado; as amd64 foram analisadas pela primeira vez e têm os mesmos números das arm64. Na 26.04, as imagens não mudaram, e os números da seção 8 continuam valendo.

## 9. Binários setuid e setgid

As `release` têm 13 (24.04) e 12 (26.04) binários com setuid ou setgid:
- todos, menos o `crontab`, vêm da própria imagem `ubuntu`: `su`, `passwd`, `chfn`, `chsh`, `gpasswd`, `newgrp`, `mount`, `umount`, `chage`, `expiry`, `unix_chkpwd` e `pam_extrausers_chkpwd` (na 26.04 não há o `newgrp`);
- o `crontab` vem do pacote `cron`, que o `entrypoint.sh` do GeoNode reinicia.

Nenhum deles é usado pelo GeoNode no container. As bases oficiais têm 2 a mais (`ssh-agent` e `ssh-keysign`), porque instalam parte dos pacotes com recomendações e acabam trazendo o `openssh-client`.

- **Rodando como root** (o padrão do GeoNode), os bits não mudam nada.
- **Rodando sem root,** `no-new-privileges` e `cap_drop: [ALL]` os neutralizam.
- **Aprimoramento proposto:** `find / -xdev -perm /6000 -type f -exec chmod a-s {} +` no fim do `runtime` deixaria a imagem sem nenhum desses binários. Precisa de nova rodada da suíte antes de ser adotado.

## 10. Problemas das bases oficiais corrigidos no build unificado

Problemas das imagens base publicadas a partir de `docker/base/ubuntu/24/Dockerfile` e `docker/base/ubuntu/26/Dockerfile` (`geonode/geonode-base:latest-ubuntu-24.04` e `latest-ubuntu-26.04`) que o Dockerfile unificado resolve. Cada item vem da leitura dos Dockerfiles e das medições das seções 5 e 9. Em ordem de impacto:

1. **Ferramentas de compilação e de empacotamento na imagem de produção.**
   - **Oficiais:** ficam na imagem final:
     - `gcc`, `build-essential`, `python3-all-dev`, `python3-dev` e as bibliotecas `-dev` (86 na 24.04, 116 na 26.04);
     - `devscripts`, `debhelper`, `pkg-kde-tools` e `sharutils`, que só serviam a um build do PROJ comentado no Dockerfile;
     - ferramentas sem uso em runtime: `vim`, `zip`, `unzip`, `curl`, `wget`, `gnupg2`, `lsb-release` e, na 26.04, `git`.

     Daí vêm os 1,44 GB e 1,66 GB e a maior parte dos CVEs: o `linux-libc-dev`, que entra com os compiladores, responde pelos 42 e 43 críticos.
   - **Unificado:** compila tudo no estágio `build` e passa ao `runtime` só o venv e as bibliotecas de que ele precisa. A `release` não tem compilador e tem no máximo um `-dev` (o `systemd-dev`, na 24.04, sem cabeçalhos C). Ela ocupa 570 MB e 666 MB e não tem CVE crítico nem alto nos pacotes do SO. Quem precisa compilar usa a `devel`.
2. **Sem `apt-get upgrade`.**
   - **Oficiais:** restam 22 (24.04) e 27 (26.04) pacotes com correção publicada e não aplicada, entre eles `apt`, `libc6` e `libbrotli1` na 26.04.
   - **Unificado:** roda `apt-get upgrade` em todos os estágios, e não resta nenhum pacote com correção pendente.
3. **Pacotes instalados com recomendações.**
   - **Oficiais:** parte dos `apt-get install` roda sem `--no-install-recommends` e traz pacotes que ninguém pediu, como o `openssh-client`, com os setuid `ssh-agent` e `ssh-keysign`. São 15 e 14 binários setuid/setgid.
   - **Unificado:** usa `--no-install-recommends` em todos os `apt-get install` e tem 13 e 12 desses binários.
4. **Bindings do GDAL sem `gdal_array`.**
   - **Oficiais:** o `pip install GDAL` roda antes de haver numpy no venv. Ler e gravar rasters como arrays numpy (`ReadAsArray`, `OpenArray`) não funciona.
   - **Unificado:** instala o numpy antes e o GDAL com `--no-build-isolation`. O smoke test confere o `gdal_array` com um ida e volta de array.
5. **Pilhas Python do sistema duplicando o venv.**
   - **Oficiais:** o apt instala, para o Python do sistema, `python3-gdal`, `python3-psycopg2`, `python3-ldap`, `python3-lxml`, `uwsgi` e `uwsgi-plugin-python3`. O GeoNode roda no venv, que não enxerga esses pacotes. Na 26.04, o `python3-gdal` traz o numpy 2.3 ao lado do 1.26 do venv.
   - **Unificado:** só o venv. O `gdal-bin` entra sem o `python3-gdal`, graças ao pacote vazio que o substitui (seção 7). Os utilitários Python do GDAL quebrados em `/usr/bin` ficam fora pelo `path-exclude` do dpkg.
6. **Pacotes do GeoNode que a base não entrega prontos.**
   - **Oficiais:** faltam `psycopg2`, `pylibmc` e `psutil` (24.04) e numpy (26.04). O uWSGI é o 2.0.31, que o GeoNode troca pelo 2.0.30 do pin. O build do GeoNode recompila tudo isso e depende dos compiladores da base.
   - **Unificado:** esses pacotes vêm compilados no venv, nas versões dos pins do GeoNode, a partir do `requirements.txt` de cada versão. O build do GeoNode não precisa de compilador.
7. **Cliente PostgreSQL fixo, e de outra versão do Ubuntu na 26.04.**
   - **Oficiais:** as duas fixam o `postgresql-client-15` no pin do PGDG. A ferramenta de backup e restauração do GeoNode (`geonode.br`) exige o mesmo major do banco, então um banco 16, 17 ou 18 obriga a editar o Dockerfile. Na 26.04, o repositório é o `noble-pgdg`, do 24.04, o que mistura pacotes de duas versões do Ubuntu.
   - **Unificado:** o cliente vem do build arg obrigatório `POSTGRESQL_CLIENT_VERSION` (padrão 18), do PGDG da própria versão (`${VERSION_CODENAME}-pgdg`) com prioridade 100. O major vai para a tag (`-pg<cliente>`), e o smoke test confere o `pg_dump`.
8. **Chave do PGDG pelo `apt-key` (24.04).**
   - **Oficial:** o `apt-key add` está obsoleto e torna a chave confiável para todos os repositórios.
   - **Unificado:** usa `signed-by`, e a chave só vale para o PGDG.
9. **Limpeza que não reduz a imagem.**
   - **Oficiais:** o `rm -rf /var/lib/apt/lists/*` fica num `RUN` separado, então as listas continuam nas camadas anteriores. O cache do pip também fica na imagem.
   - **Unificado:** limpa as listas no mesmo `RUN` de cada instalação e usa `pip install --no-cache-dir`.
10. **Só amd64.**
    - **Oficiais:** só existem em amd64. Em Apple Silicon, AWS Graviton ou Ampere, rodam emuladas.
    - **Unificado:** o mesmo Dockerfile gera amd64 e arm64, sem mudança, e as quatro tags foram construídas como manifest lists com as duas arquiteturas (seção 8). A publicação continua dependendo dos mantenedores (seção 12).
11. **Sem verificação.**
    - **Oficiais:** nada testa a imagem depois do build.
    - **Unificado:** o smoke test roda no fim do `runtime` e da `devel`, e o build falha se algum item falhar. Ele fica instalado na imagem como `geonode-base-smoke-test`, para as imagens derivadas.
12. **Dois Dockerfiles que divergem.**
    - **Oficiais:** um por versão do Ubuntu, com diferenças que não vêm da versão:
      - só a 26.04 define `DEBIAN_FRONTEND`, cria `/usr/src/geonode` e instala `git`;
      - só a 24.04 instala `libmemcached-dev`;
      - só a 24.04 tem um `RUN . /usr/src/venv/bin/activate` sem efeito e o comentário obsoleto "will install python3.10".
    - **Unificado:** um único Dockerfile. O que muda por versão fica no `requirements.txt` do diretório e em dois build args (`EXTRA_BUILD_PACKAGES` e `POSTGRESQL_CLIENT_VERSION`).

## 11. Aprimoramentos e vantagens

| Aspecto | Bases oficiais | Base multi-stage unificada |
|---|---|---|
| Tamanho da imagem de produção | 1,44 GB / 1,66 GB | 570 MB / 666 MB |
| Compiladores e `-dev` | sim (86 / 116 `-dev`) | nenhum compilador; no máximo o `systemd-dev` (24.04) |
| CVEs nos pacotes do SO | 3.468 / 3.750, com 42 / 43 críticos | 108 / 93, nenhum crítico ou alto |
| Correções do Ubuntu | 22 / 27 pacotes com correção pendente | `apt-get upgrade` em todos os estágios: nenhuma pendente |
| Bibliotecas de runtime | escolhidas à mão | detectadas pelo `ldd` |
| Bindings do GDAL | sem `gdal_array` | com `gdal_array` |
| Bindings Python do sistema | duplicam o venv (e, na 26.04, um segundo numpy) | só o venv |
| Pacotes compilados para o GeoNode | o build do GeoNode compila de novo (`psycopg2`, `pylibmc`, numpy, uWSGI na versão do pin) | já compilados, nas versões dos pins |
| Cliente PostgreSQL | 15 fixo; na 26.04, do PGDG do 24.04 | escolhido no build, do PGDG da própria versão, com prioridade 100 |
| Dockerfiles | um por versão | um único, com um diretório por versão só com o `requirements.txt` |
| Verificação | nenhuma | smoke test no build e na imagem |
| Imagem para compilar | — | `devel` |
| Arquiteturas | só amd64 publicadas | amd64 e arm64 com o mesmo Dockerfile |
| Compatibilidade | — | mesmos caminhos: os Dockerfiles do GeoNode e do geonode-project funcionam sem mudança |

## 12. Recomendações

- **Rodar a suíte do GeoNode também em amd64** antes de publicar. Em arm64 ela já passou sobre as imagens unificadas (seção 4).
- **Versão do cliente PostgreSQL na tag:** `ubuntu-<tag>-pg<cliente>` para a `release` e `-devel` para a `devel`. A ferramenta de backup e restauração do GeoNode (`geonode.br`) exige o mesmo major do banco.
- **Aos mantenedores do GeoNode: publicar imagens também em arm64.** Hoje as imagens oficiais só existem em amd64: a base, a do GeoNode e as dos serviços (`geonode/postgis`, `geonode/geoserver`, `geonode/geoserver_data`, `geonode/nginx`). Em máquinas arm64 (Apple Silicon, AWS Graviton, Ampere), elas só rodam emuladas, mais lentas e sujeitas a falhas como a corrida de boot do `security`. Este Dockerfile constrói as duas arquiteturas sem mudança, e `docker buildx build --platform linux/amd64,linux/arm64` nos workflows do GitHub Actions faria as mesmas tags servirem às duas.
- **Build multi-arquitetura em máquinas nativas,** sem emulação. Os builds amd64 emulados levaram de 2,5 a 5 vezes mais que os arm64 nativos (seção 8.1), e a compilação do numpy da 26.04 ficou 4,5 vezes mais lenta em amd64.
- **Remover os bits setuid/setgid** no fim do `runtime` (seção 9).
- **numpy 2.x no GeoNode.** O pin `numpy==1.26.*` é da master. O único uso direto, em `geonode/upload/handlers/tiles3d/utils.py`, usa `np.NaN`, removido no numpy 2.0 (precisaria virar `np.nan`). Ganhos:
  - wheels para Python 3.14: a base 26.04 deixaria de compilar o numpy e de precisar do `libopenblas-dev`;
  - uma série mantida: a 1.26 está encerrada.
- **No GeoNode, não na base:**
  - `pip install --no-cache-dir` no `Dockerfile` da raiz, o que tira de 147 MB a 195 MB das imagens da 5.0.x;
  - atualizar o Pillow e o PyJWT da 5.0.x.

## 13. Como reproduzir

```bash
# A partir da raiz do repositório
# Ubuntu 26.04 (padrões) e Ubuntu 24.04, em amd64 e arm64 (manifest list)
podman build --platform linux/amd64,linux/arm64 --manifest docker.io/ndscprm/geonode-base:ubuntu-26.04-pg18 \
  --target release docker/base/ubuntu/multi-stage
podman build --platform linux/amd64,linux/arm64 --manifest docker.io/ndscprm/geonode-base:ubuntu-26.04-pg18-devel \
  --target devel docker/base/ubuntu/multi-stage
podman build --platform linux/amd64,linux/arm64 --manifest docker.io/ndscprm/geonode-base:ubuntu-24.04-pg15 \
  --target release --build-arg UBUNTU_RELEASE=24 --build-arg EXTRA_BUILD_PACKAGES=libmemcached-dev \
  --build-arg POSTGRESQL_CLIENT_VERSION=15 docker/base/ubuntu/multi-stage
podman build --platform linux/amd64,linux/arm64 --manifest docker.io/ndscprm/geonode-base:ubuntu-24.04-pg15-devel \
  --target devel --build-arg UBUNTU_RELEASE=24 --build-arg EXTRA_BUILD_PACKAGES=libmemcached-dev \
  --build-arg POSTGRESQL_CLIENT_VERSION=15 docker/base/ubuntu/multi-stage

# Smoke test de cada arquitetura
podman run --rm --platform linux/amd64 docker.io/ndscprm/geonode-base:ubuntu-26.04-pg18 geonode-base-smoke-test
podman run --rm --platform linux/arm64 docker.io/ndscprm/geonode-base:ubuntu-26.04-pg18 geonode-base-smoke-test

# Suíte do GeoNode sobre a base (todos os grupos; logs em ~/.cache/geonode-base-tests/logs/)
./docker/base/ubuntu/multi-stage/geonode-tests --ref master --base docker.io/ndscprm/geonode-base:ubuntu-26.04-pg18
./docker/base/ubuntu/multi-stage/geonode-tests --ref 5.0.x --base docker.io/ndscprm/geonode-base:ubuntu-24.04-pg15
```

O `geonode-tests` precisa do bash 4.3 ou mais novo (no macOS, o do Homebrew), do git e do Docker ou Podman com compose.

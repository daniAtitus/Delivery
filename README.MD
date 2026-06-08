# 🛵 Sistema de Delivery

Aplicação de pedidos online desenvolvida com **FastAPI**, **Redis** e **RabbitMQ**.

- **Cliente** faz pedidos pela interface web
- **FastAPI** recebe, valida e persiste os pedidos
- **RabbitMQ** enfileira os pedidos para a cozinha processar
- **Redis** armazena o status em tempo real e faz cache do cardápio
- **Worker** consome a fila e simula o preparo dos pedidos

---

## Pré-requisitos

Antes de começar, certifique-se de ter instalado:

- [Python 3.11+](https://www.python.org/downloads/)
- [Docker Desktop](https://www.docker.com/products/docker-desktop)

---

## Estrutura do projeto

```
delivery/
├── server/
│   ├── main.py              # FastAPI — rotas da API
│   ├── models.py            # Tabelas (SQLAlchemy) e schemas (Pydantic)
│   ├── database.py          # Conexão com SQLite
│   ├── redis_client.py      # Cache e status em tempo real
│   ├── rabbit_publisher.py  # Publica pedidos na fila
│   └── worker.py            # Consome a fila e processa pedidos
├── client/
│   ├── index.html           # Tela do cliente
│   ├── cozinha.html         # Painel da cozinha
│   └── style.css
├── docker-compose.yml       # Redis + RabbitMQ
├── requirements.txt
└── README.md
```

---

## Instalação

### 1. Clone ou baixe o projeto

```bash
cd delivery
```

### 2. Crie e ative o ambiente virtual

```bash
python -m venv venv
```

```bash
# Windows
venv\Scripts\activate

# Mac / Linux
source venv/bin/activate
```

> O terminal deve exibir `(venv)` no início da linha após a ativação.

### 3. Instale as dependências Python

```bash
pip install -r requirements.txt
```

### 4. Suba o Redis e o RabbitMQ via Docker

Certifique-se de que o **Docker Desktop está aberto e rodando**, depois execute:

```bash
docker-compose up -d
```

Verifique se os containers estão de pé:

```bash
docker-compose ps
```

Você deve ver `redis` e `rabbitmq` com status `running`.

---

## Rodando o projeto

Você precisará de **dois terminais** abertos simultaneamente.
Em ambos, o ambiente virtual deve estar ativo e você deve estar dentro da pasta `server/`.

```bash
cd server
```

**Terminal 1 — Servidor FastAPI**

```bash
uvicorn main:app --reload
```

**Terminal 2 — Worker da cozinha**

```bash
python worker.py
```

> O servidor e o worker são processos independentes. Se o worker for encerrado, os pedidos continuam sendo recebidos e ficam acumulados na fila até ele voltar.

---

## Acessando a aplicação

Com tudo rodando, abra no navegador:

| Endereço | Descrição |
|---|---|
| http://localhost:8000/static/index.html | Tela do cliente — fazer pedidos |
| http://localhost:8000/static/cozinha.html | Painel da cozinha — acompanhar fila |
| http://localhost:8000/docs | Documentação interativa da API |
| http://localhost:15672 | Painel do RabbitMQ (guest / guest) |

---

## Como usar

1. Abra a **tela do cliente** e selecione itens do cardápio
2. Informe o endereço e clique em **Fazer pedido**
3. Acompanhe o status do pedido atualizar automaticamente na mesma tela
4. No **painel da cozinha** você vê o pedido aparecer e mudar de status em tempo real
5. No **Terminal 2** você vê o worker processar o pedido e atualizar o Redis

---

## Encerrando

Para parar os servidores, pressione `Ctrl+C` em cada terminal.

Para parar os containers Docker:

```bash
# Mantém os dados salvos
docker-compose down

# Para os containers e apaga os dados
docker-compose down -v
```

---

## Erros comuns

**`ModuleNotFoundError`**
O ambiente virtual não está ativo. Execute `venv\Scripts\activate` (Windows) ou `source venv/bin/activate` (Mac/Linux) antes de qualquer comando Python.

**`Connection refused` (Redis ou RabbitMQ)**
O Docker Desktop não está rodando ou os containers não foram iniciados. Execute `docker-compose up -d` e tente novamente.

**`Address already in use` na porta 8000**
Outra aplicação está usando a porta. Rode com uma porta diferente:
```bash
uvicorn main:app --reload --port 8001
```
E atualize a variável `API` nos arquivos `index.html` e `cozinha.html` para `http://localhost:8001`.

**Banco não criado**
O arquivo `delivery.db` é criado automaticamente na pasta `server/` na primeira vez que o servidor sobe. Se não aparecer, verifique se o `init_db()` está sendo chamado no startup do `main.py`.
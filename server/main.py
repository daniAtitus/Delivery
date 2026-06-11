from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from databse import get_db, engine
from models import Base, Pedido as PedidoModel
from redis_client import get_status, set_status, get_cardapio_cache, set_cardapio_cache
from rabbit_publisher import publicar_pedido
from models import PedidoCreate, PedidoResponse, StatusUpdate

from sqlalchemy.orm import Session
from fastapi import Depends
from typing import Optional

app = FastAPI(
    title="Sistema de Delivery",
    description="API REST para gerenciamento de pedidos com Redis e RabbitMQ",
    version="1.0.0"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


app.mount("/static", StaticFiles(directory="../client"), name="static")

@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    print("✅ Banco de dados pronto")


@app.get("/")
def root():
    return {"status": "online", "docs": "/docs"}


CARDAPIO = [
    {"id": 1, "nome": "Pizza Margherita",  "preco": 35.00},
    {"id": 2, "nome": "Pizza Calabresa",   "preco": 38.00},
    {"id": 3, "nome": "Hamburguer Clássico", "preco": 28.00},
    {"id": 4, "nome": "Batata Frita",      "preco": 15.00},
    {"id": 5, "nome": "Refrigerante",      "preco": 8.00},
]

@app.get("/cardapio")
def listar_cardapio():
    # Tenta pegar do cache Redis primeiro
    cached = get_cardapio_cache()
    if cached:
        print("📦 Cardápio servido do cache Redis")
        return cached

    # Cache miss: usa o cardápio fixo (ou buscaria do banco)
    print("🗄️  Cardápio buscado da fonte e salvo no cache")
    set_cardapio_cache(CARDAPIO)
    return CARDAPIO



# Recebe os itens escolhidos pelo cliente.
#
# Fluxo:
#1-Valida os dados (Pydantic faz isso automaticamente)
#2-Salva o pedido no banco com status "recebido"
#3-Salva o status inicial no Redis
#4-Publica mensagem no RabbitMQ para a cozinha processar
#5-Retorna o pedido criado para o cliente


@app.post("/pedido", response_model=PedidoResponse, status_code=201)
def criar_pedido(pedido: PedidoCreate, db: Session = Depends(get_db)):
    db_pedido = PedidoModel(
        itens=str(pedido.itens),       
        endereco=pedido.endereco,
        status="recebido"
    )
    db.add(db_pedido)
    db.commit()
    db.refresh(db_pedido) 

    set_status(db_pedido.id, "recebido")

    publicar_pedido(db_pedido.id)

    print(f"✅ Pedido #{db_pedido.id} criado e enviado para a fila")

    return db_pedido



@app.get("/pedido/{pedido_id}")
def consultar_pedido(pedido_id: int, db: Session = Depends(get_db)):
    status_redis = get_status(pedido_id)
    if status_redis:
        print(f"⚡ Status do pedido #{pedido_id} servido do Redis")
        return {"id": pedido_id, "status": status_redis}


    pedido = db.query(PedidoModel).filter(PedidoModel.id == pedido_id).first()
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")

    return {"id": pedido.id, "status": pedido.status}



@app.get("/pedidos")
def listar_pedidos(status: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(PedidoModel)


    if status:
        query = query.filter(PedidoModel.status == status)

    pedidos = query.order_by(PedidoModel.id.desc()).all()
    return pedidos


@app.patch("/pedido/{pedido_id}/status")
def atualizar_status(pedido_id: int, body: StatusUpdate, db: Session = Depends(get_db)):

    status_validos = ["recebido", "preparando", "pronto", "entregue"]
    if body.status not in status_validos:
        raise HTTPException(
            status_code=400,
            detail=f"Status inválido. Use: {status_validos}"
        )

    
    pedido = db.query(PedidoModel).filter(PedidoModel.id == pedido_id).first()
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")

    pedido.status = body.status
    db.commit()

    set_status(pedido_id, body.status)

    print(f"🔄 Pedido #{pedido_id} → {body.status}")
    return {"id": pedido_id, "status": body.status}

@app.delete("/pedido/{pedido_id}")
def remover_pedido(pedido_id: int, db: Session = Depends(get_db)):
    # 1. Verifica se o pedido existe
    pedido = db.query(PedidoModel).filter(PedidoModel.id == pedido_id).first()
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")

    # 2. Regra de negócio: apenas pedidos "entregues" podem ser apagados
    if pedido.status != "entregue":
        raise HTTPException(status_code=400, detail="Apenas pedidos entregues podem ser removidos")

    # 3. Remove do SQLite
    db.delete(pedido)
    db.commit()

    # 4. Remove a chave do status no Redis
    from redis_client import r
    r.delete(f"pedido:{pedido_id}:status")

    print(f"🗑️ Pedido #{pedido_id} removido do sistema")
    return {"mensagem": f"Pedido #{pedido_id} removido com sucesso"}
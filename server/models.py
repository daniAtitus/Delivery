from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.sql import func
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from databse import Base


class Pedido(Base):
    """
    Representa a tabela 'pedidos' no banco.

    Quando o init_db() rodar, o SQLAlchemy vai
    criar exatamente esta tabela:

    CREATE TABLE pedidos (
        id        INTEGER PRIMARY KEY,
        itens     TEXT    NOT NULL,
        endereco  TEXT    NOT NULL,
        status    TEXT    DEFAULT 'recebido',
        criado_em DATETIME DEFAULT now()
    );
    """

    __tablename__ = "pedidos"  

    id = Column(
        Integer,
        primary_key=True,
        index=True         
    )

    itens = Column(String, nullable=False)

    endereco = Column(String, nullable=False)


    status = Column(String, default="recebido")

    criado_em = Column(DateTime, server_default=func.now())



class PedidoCreate(BaseModel):
    """
    Schema de ENTRADA — formato do JSON que o
    cliente manda no POST /pedido.

    O FastAPI valida automaticamente:
    - Se os campos obrigatórios estão presentes
    - Se os tipos estão corretos
    - Se a lista de itens não está vazia
    """
    itens: list[int]       
    endereco: str           


class PedidoResponse(BaseModel):
    """
    Schema de SAÍDA — formato do JSON que a API
    devolve após criar ou consultar um pedido.
    """
    id: int
    itens: str              
    endereco: str
    status: str
    criado_em: Optional[datetime] = None

    class Config:
        from_attributes = True


class StatusUpdate(BaseModel):
    """
    Schema para o PATCH /pedido/{id}/status.
    O worker manda apenas o novo status.
    """
    status: str           

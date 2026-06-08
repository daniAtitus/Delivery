import redis
import json
from typing import Optional

r = redis.Redis(
    host="localhost",   
    port=6379,          
    db=0,              
    decode_responses=True
)


def testar_conexao() -> bool:
    try:
        r.ping()
        print("✅ Redis conectado")
        return True
    except redis.ConnectionError:
        print("❌ Redis não encontrado — certifique-se que está rodando")
        return False




STATUS_TTL_SEGUNDOS = 60 * 60 * 2 


def set_status(pedido_id: int, status: str) -> None:
    """
    Salva ou atualiza o status de um pedido no Redis.

    Chamada em dois momentos:
    - Quando o pedido é criado (status "recebido")
    - Quando o worker muda o status
    """
    chave = f"pedido:{pedido_id}:status"
    r.setex(chave, STATUS_TTL_SEGUNDOS, status)

    print(f"📝 Redis: pedido:{pedido_id} → {status}")


def get_status(pedido_id: int) -> Optional[str]:
    """
    Busca o status atual de um pedido no Redis.

    Retorna None se:
    - O pedido não existe
    - O TTL expirou e o Redis apagou a chave
    Nesse caso, o FastAPI faz fallback para o banco.
    """
    chave = f"pedido:{pedido_id}:status"
    status = r.get(chave)
    return status  


def get_ttl_status(pedido_id: int) -> int:
    """
    Retorna quantos segundos faltam para o status
    expirar no Redis. Útil para debug.
    -1 = sem expiração
    -2 = chave não existe
    """
    chave = f"pedido:{pedido_id}:status"
    return r.ttl(chave)



CARDAPIO_TTL_SEGUNDOS = 60 


def get_cardapio_cache() -> Optional[list]:
    """
    Tenta buscar o cardápio do cache Redis.

    Retorna a lista de itens se existir no cache,
    ou None se o cache estiver vazio/expirado.
    """
    dados = r.get("cardapio")
    if dados:
        return json.loads(dados)
    return None


def set_cardapio_cache(cardapio: list) -> None:
    """
    Salva o cardápio no cache Redis por 60 segundos.

    json.dumps converte a lista Python para string JSON
    antes de salvar, porque o Redis só aceita strings.
    """
    r.setex("cardapio", CARDAPIO_TTL_SEGUNDOS, json.dumps(cardapio))
    print(f"📦 Cardápio salvo no cache por {CARDAPIO_TTL_SEGUNDOS}s")


def invalidar_cardapio_cache() -> None:
    """
    Apaga o cache do cardápio antes do TTL expirar.

    Útil quando um produto é adicionado ou removido:
    em vez de esperar 60 segundos, você invalida
    na hora e a próxima requisição já pega o dado novo.
    """
    r.delete("cardapio")
    print("🗑️  Cache do cardápio invalidado")



def listar_chaves(padrao: str = "*") -> list:
    """
    Lista todas as chaves no Redis que combinam
    com o padrão. Por padrão lista todas.

    Exemplos:
      listar_chaves()              → todas as chaves
      listar_chaves("pedido:*")   → só chaves de pedidos
    """
    return r.keys(padrao)


def limpar_tudo() -> None:
    """
    Apaga TODAS as chaves do banco 0 do Redis.
    Use apenas em desenvolvimento para resetar o estado.
    """
    r.flushdb()
    print("🧹 Redis limpo")

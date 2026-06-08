import pika
import json
import time
import requests

from rabbit_publisher import get_conexao, FILA_PEDIDOS
from redis_client import set_status


API_URL = "http://localhost:8000"


TEMPO_PREPARO_SEGUNDOS = 10 

def atualizar_status(pedido_id: int, novo_status: str) -> None:
    """
    Atualiza o status do pedido em dois lugares:
      1. Redis  → para o cliente ver na hora (polling)
      2. Banco  → para persistência permanente

    O Redis é atualizado direto aqui (rápido).
    O banco é atualizado via chamada HTTP ao FastAPI.
    """
    set_status(pedido_id, novo_status)


    try:
        response = requests.patch(
            f"{API_URL}/pedido/{pedido_id}/status",
            json={"status": novo_status}
        )
        if response.status_code == 200:
            print(f"   ✅ Banco atualizado: pedido #{pedido_id} → {novo_status}")
        else:
            print(f"   ⚠️  Erro ao atualizar banco: {response.status_code}")
    except requests.exceptions.ConnectionError:
        print(f"   ⚠️  API indisponível — status salvo só no Redis por ora")



def processar_pedido(ch, method, properties, body):
    """
    Processa um pedido consumido da fila RabbitMQ.

    Fluxo completo:
      recebido → preparando → pronto
    """

    dados = json.loads(body)
    pedido_id = dados["pedido_id"]

    print(f"\n🔔 Novo pedido recebido da fila!")
    print(f"   Pedido ID : #{pedido_id}")
    print(f"   Enviado em: {dados.get('enviado_em', '?')}")


    print(f"\n👨‍🍳 Iniciando preparo do pedido #{pedido_id}...")
    atualizar_status(pedido_id, "preparando")

    print(f"   ⏳ Preparando por {TEMPO_PREPARO_SEGUNDOS} segundos...")
    time.sleep(TEMPO_PREPARO_SEGUNDOS)


    atualizar_status(pedido_id, "pronto")
    print(f"   🍕 Pedido #{pedido_id} pronto para entrega!\n")

    ch.basic_ack(delivery_tag=method.delivery_tag)



def iniciar_worker():
    """
    Conecta ao RabbitMQ e fica escutando a fila
    indefinidamente, processando pedidos conforme chegam.
    """
    print("🚀 Worker da cozinha iniciando...")
    print(f"   Fila   : {FILA_PEDIDOS}")
    print(f"   API    : {API_URL}")
    print(f"   Preparo: {TEMPO_PREPARO_SEGUNDOS}s por pedido")
    print("\n⏳ Aguardando pedidos... (Ctrl+C para parar)\n")

    conexao = get_conexao()
    canal = conexao.channel()

    canal.queue_declare(queue=FILA_PEDIDOS, durable=True)

    canal.basic_qos(prefetch_count=1)

    canal.basic_consume(
        queue=FILA_PEDIDOS,
        on_message_callback=processar_pedido,
        auto_ack=False
    )

    try:
        canal.start_consuming()
    except KeyboardInterrupt:
        print("\n🛑 Worker encerrado pelo usuário")
        canal.stop_consuming()
    finally:
        if conexao and not conexao.is_closed:
            conexao.close()



if __name__ == "__main__":
    iniciar_worker()

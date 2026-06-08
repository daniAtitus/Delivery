import pika
import json
from datetime import datetime


def get_conexao():
    """
    Cria e retorna uma nova conexão com o RabbitMQ.

    Criamos uma nova conexão a cada publicação
    em vez de manter uma conexão permanente.
    Isso é mais simples e seguro para uma API
    que recebe requisições esporádicas.
    """
    credenciais = pika.PlainCredentials(
        username="guest",
        password="guest"
    )

    parametros = pika.ConnectionParameters(
        host="localhost",       
        port=5672,              
        virtual_host="/",       
        credentials=credenciais,
        connection_attempts=3,  
        retry_delay=2           
    )

    return pika.BlockingConnection(parametros)



FILA_PEDIDOS = "pedidos"

def publicar_pedido(pedido_id: int) -> bool:
    """
    Publica uma mensagem na fila do RabbitMQ
    avisando que um novo pedido foi criado.

    O worker da cozinha fica escutando essa fila
    e vai consumir essa mensagem para processar
    o pedido.

    Retorna True se publicou com sucesso,
    False se houve algum erro.
    """
    conexao = None
    try:
    
        conexao = get_conexao()

        canal = conexao.channel()
        canal.queue_declare(queue=FILA_PEDIDOS, durable=True)

        mensagem = json.dumps({
            "pedido_id": pedido_id,
            "enviado_em": datetime.now().isoformat()
        })

        
        canal.basic_publish(
            exchange="",            
            routing_key=FILA_PEDIDOS,  
            body=mensagem,
            properties=pika.BasicProperties(
                delivery_mode=2     
                                    
            )
        )

        print(f"📨 Pedido #{pedido_id} publicado na fila '{FILA_PEDIDOS}'")
        return True

    except pika.exceptions.AMQPConnectionError:
        print("❌ Erro: não foi possível conectar ao RabbitMQ")
        print("   Verifique se o RabbitMQ está rodando (docker-compose up)")
        return False

    except Exception as e:
        print(f"❌ Erro inesperado ao publicar mensagem: {e}")
        return False

    finally:
        if conexao and not conexao.is_closed:
            conexao.close()

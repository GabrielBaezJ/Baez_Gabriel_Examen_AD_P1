import os
import socket
import sys
import threading


# Host y puertos del servidor; pueden sobreescribirse mediante variables de entorno.
HOST = os.getenv("CHAT_HOST", "127.0.0.1")
PORT = int(os.getenv("CHAT_PORT", "8765"))
ADMIN_PORT = int(os.getenv("CHAT_ADMIN_PORT", "8766"))


def recibir_mensajes(archivo):
    # Lee mensajes del servidor en paralelo con la entrada del usuario.
    try:
        # Cada línea recibida representa un mensaje completo del protocolo.
        for linea in archivo:
            print(linea.decode("utf-8").rstrip(), flush=True)
    except (OSError, UnicodeDecodeError) as error:
        # Se informa si el socket o el texto recibido no se pueden procesar.
        print(f"Error al recibir mensajes: {error}", flush=True)
    else:
        # El bucle termina normalmente cuando el servidor cierra la conexión.
        print("Se cerró la conexión con el servidor.", flush=True)


def consola_servidor():
    try:
        # El canal administrativo es distinto al puerto usado por los clientes.
        conexion = socket.create_connection((HOST, ADMIN_PORT))
    except OSError as error:
        print(
            "No fue posible conectar con la consola del servidor "
            f"en {HOST}:{ADMIN_PORT}: {error}"
        )
        return

    with conexion:
        # Mantiene la conexión abierta para enviar varios mensajes.
        print("Consola del servidor. Escribe /salir para terminar.")
        try:
            while True:
                mensaje = input("Servidor> ")
                if mensaje.strip() == "/salir":
                    break
                if mensaje.strip():
                    # El salto de línea permite que el servidor separe cada mensaje recibido.
                    conexion.sendall(f"{mensaje}\n".encode("utf-8"))
        except EOFError:
            # La entrada terminó, así que se cierra la consola administrativa.
            return
        except OSError as error:
            print(f"Error al enviar el mensaje del servidor: {error}")


def main():
    # El argumento especial inicia la consola que envía mensajes como servidor.
    if sys.argv[1:] == ["--servidor"]:
        consola_servidor()
        return
    # No se aceptan argumentos adicionales para evitar modos de ejecución ambiguos.
    if sys.argv[1:]:
        print("Uso: python 08_web_cliente.py [--servidor]")
        return

    try:
        # El cliente abre una conexión TCP al puerto de chat del servidor.
        cliente = socket.create_connection((HOST, PORT))
    except OSError as error:
        print(f"No fue posible conectar con {HOST}:{PORT}: {error}")
        return

    with cliente:
        # El archivo de lectura facilita recibir el mensaje de asignación y el chat por líneas.
        archivo = cliente.makefile("rb")
        try:
            # El servidor asigna el nombre según el orden de conexión.
            respuesta = archivo.readline().decode("utf-8").rstrip("\r\n")
        except (OSError, UnicodeDecodeError) as error:
            print(f"No se pudo obtener el nombre asignado por el servidor: {error}")
            archivo.close()
            return

        # El protocolo comunica al cliente si se asignó un nombre o se rechazó la conexión.
        if respuesta.startswith("ERROR:"):
            print(respuesta.removeprefix("ERROR:").strip())
            archivo.close()
            return
        if not respuesta.startswith("ASIGNADO:"):
            print("El servidor envió una respuesta de conexión no válida.")
            archivo.close()
            return

        # Conserva el nombre que asignó el servidor para mostrarlo al usuario.
        nombre = respuesta.removeprefix("ASIGNADO:")
        print(f"Conectado como {nombre}. Escribe /salir para terminar.")

        # Un hilo escucha el socket para que la entrada de teclado no bloquee los mensajes.
        receptor = threading.Thread(
            target=recibir_mensajes, args=(archivo,), daemon=True
        )
        receptor.start()

        try:
            # El hilo principal lee mensajes escritos por el usuario y los manda al servidor.
            while True:
                mensaje = input()
                if mensaje.strip() == "/salir":
                    break
                if mensaje.strip():
                    cliente.sendall(f"{mensaje}\n".encode("utf-8"))
        except (BrokenPipeError, OSError) as error:
            print(f"Error al enviar el mensaje: {error}")
        finally:
            try:
                # El cierre de escritura informa al servidor que este cliente terminó.
                cliente.shutdown(socket.SHUT_WR)
            except OSError as error:
                print(f"Error al cerrar el canal de envío: {error}")
            # Cierra el lector después de notificar al servidor la desconexión.
            archivo.close()


if __name__ == "__main__":
    # Inicia el modo elegido solo cuando se ejecuta este archivo directamente.
    main()

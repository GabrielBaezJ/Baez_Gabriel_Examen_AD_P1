import os
import socket
import threading


# Dirección, puertos y nombres que utiliza el servidor dentro del contenedor.
HOST = "0.0.0.0"
PORT = int(os.getenv("CHAT_PORT", "8765"))
ADMIN_PORT = int(os.getenv("CHAT_ADMIN_PORT", "8766"))
NOMBRES_CLIENTES = ("Cliente 1", "Cliente 2")
# Este registro compartido guarda socket, nombre y bloqueo individual de cada cliente.
clientes = {}
# Protege las modificaciones y lecturas simultáneas del registro compartido.
clientes_lock = threading.Lock()


def difundir(mensaje):
    # Se usa una línea UTF-8 como unidad del protocolo TCP.
    datos = f"{mensaje}\n".encode("utf-8")
    # Se copia el registro bajo el bloqueo y se envía después de liberarlo.
    with clientes_lock:
        conectados = list(clientes.items())

    # Cada bloqueo evita que dos hilos intercalen bytes al enviar al mismo cliente.
    for conexion, (nombre, bloqueo_envio) in conectados:
        try:
            with bloqueo_envio:
                conexion.sendall(datos)
        except OSError:
            # El manejador de esa conexión la quitará del registro al detectar el cierre.
            print(f"Se perdió la conexión con {nombre}.")


def atender_cliente(conexion, direccion):
    # Asigna un nombre, retransmite los mensajes y limpia la conexión al salir.
    # makefile permite recorrer los datos entrantes línea por línea.
    archivo = conexion.makefile("rb")
    nombre = ""
    # Indica si el socket llegó a registrarse y, por tanto, debe anunciar su salida.
    estaba_conectado = False
    try:
        # La reserva del nombre y el registro ocurren juntos para evitar asignaciones duplicadas.
        with clientes_lock:
            nombres_ocupados = {datos[0] for datos in clientes.values()}
            nombre = next(
                (candidato for candidato in NOMBRES_CLIENTES if candidato not in nombres_ocupados),
                "",
            )
            if not nombre:
                # El servidor rechaza más conexiones cuando ambos nombres están ocupados.
                conexion.sendall(b"ERROR: Ya hay dos clientes conectados.\n")
                return

            # El cliente recibe su nombre antes de que comiencen los mensajes del chat.
            conexion.sendall(f"ASIGNADO:{nombre}\n".encode("utf-8"))
            clientes[conexion] = (nombre, threading.Lock())
            estaba_conectado = True

        # Informa a todos que el cliente ya se encuentra disponible en el chat.
        print(f"{nombre} se conectó desde {direccion}.")
        difundir(f"{nombre} se ha conectado.")

        # El hilo permanece leyendo mensajes hasta que el cliente cierra el socket.
        for linea in archivo:
            mensaje = linea.decode("utf-8").rstrip("\r\n")
            if mensaje.strip():
                print(f"{nombre}: {mensaje}")
                difundir(f"{nombre}: {mensaje}")
    except (OSError, UnicodeDecodeError) as error:
        print(f"Error con el cliente {direccion}: {error}")
    finally:
        # Cierra el lector y el socket, y libera el nombre para una conexión futura.
        archivo.close()
        with clientes_lock:
            clientes.pop(conexion, None)
        conexion.close()
        if estaba_conectado:
            print(f"{nombre} se desconectó.")
            difundir(f"{nombre} se ha desconectado.")


def atender_consola_servidor(conexion, direccion):
    # Recibe los mensajes escritos en la consola remota y los distribuye.
    archivo = conexion.makefile("rb")
    try:
        # Cada línea recibida desde --servidor se publica como mensaje del servidor.
        for linea in archivo:
            mensaje = linea.decode("utf-8").rstrip("\r\n")
            if mensaje.strip():
                print(f"Servidor: {mensaje}")
                difundir(f"Servidor: {mensaje}")
    except (OSError, UnicodeDecodeError) as error:
        print(f"Error con la consola del servidor {direccion}: {error}")
    finally:
        # La consola de envío es independiente de los sockets de los clientes del chat.
        archivo.close()
        conexion.close()


def aceptar_consolas(servidor, detener):
    # Acepta conexiones de la consola mientras el servidor siga activo.
    while not detener.is_set():
        try:
            # Espera una consola y crea un hilo para no bloquear otras conexiones.
            conexion, direccion = servidor.accept()
        except OSError:
            # El socket se cierra al apagar el servidor; en ese caso se termina el hilo.
            if detener.is_set():
                return
            raise

        # La consola puede enviar varias líneas de mensajes por la misma conexión.
        hilo = threading.Thread(
            target=atender_consola_servidor,
            args=(conexion, direccion),
            daemon=True,
        )
        hilo.start()


def main():
    # Prepara los puertos de chat y consola e inicia sus hilos de atención.
    detener = threading.Event()
    # Se abren dos sockets: uno para el chat y otro para los mensajes del servidor.
    with (
        socket.socket(socket.AF_INET, socket.SOCK_STREAM) as servidor,
        socket.socket(socket.AF_INET, socket.SOCK_STREAM) as consola,
    ):
        # Permite reiniciar pronto y publica ambos puertos en todas las interfaces.
        for listener, puerto in ((servidor, PORT), (consola, ADMIN_PORT)):
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listener.bind((HOST, puerto))
            listener.listen()

        # El hilo de administración acepta mensajes mientras el principal atiende clientes.
        hilo_consola = threading.Thread(
            target=aceptar_consolas,
            args=(consola, detener),
            daemon=True,
        )
        hilo_consola.start()
        print(f"Servidor escuchando en {HOST}:{PORT}; consola en {HOST}:{ADMIN_PORT}...")

        try:
            # Cada cliente del chat se procesa en su propio hilo.
            while True:
                conexion, direccion = servidor.accept()
                hilo = threading.Thread(
                    target=atender_cliente,
                    args=(conexion, direccion),
                    daemon=True,
                )
                hilo.start()
        except KeyboardInterrupt:
            # Ctrl+C detiene el ciclo principal y activa el cierre ordenado.
            print("\nServidor detenido.")
        finally:
            # Notifica al hilo de administración que ya no debe aceptar conexiones.
            detener.set()


if __name__ == "__main__":
    # Ejecuta el servidor solo cuando este archivo es el programa principal.
    main()
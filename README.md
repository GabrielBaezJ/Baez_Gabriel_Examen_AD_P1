# Chat TCP con sockets e hilos

Aplicación de chat en Python. El servidor corre en Docker y atiende hasta dos clientes con conexiones TCP concurrentes. Los nombres `Cliente 1` y `Cliente 2` se asignan automáticamente según el orden de conexión. Los mensajes de los clientes y de la consola del servidor se difunden a todos los clientes conectados.

## Requisitos

- Docker Desktop con Docker Compose.
- Python 3 instalado en Windows para ejecutar los clientes.
- No se necesitan paquetes adicionales de Python.

## Iniciar el servidor

Abre PowerShell en la carpeta del proyecto y ejecuta:

```powershell
docker compose up --build
```

Espera a que aparezca un mensaje indicando que el servidor escucha en los puertos `8765` y `8766`. Deja esta terminal abierta. No escribas los mensajes del chat en ella; el servidor corre en el contenedor y recibe los mensajes desde otra terminal.

## Iniciar los dos clientes

Abre dos terminales independientes de VS Code en la carpeta del proyecto. En cada una ejecuta:

```powershell
python .\08_web_cliente.py
```

El primer proceso conectado será `Cliente 1` y el segundo `Cliente 2`. Escribe un mensaje y presiona Enter para enviarlo. Cada cliente puede escribir `/salir` para desconectarse.

El servidor admite como máximo dos clientes activos. Si uno se desconecta, el siguiente cliente que se conecte ocupará su lugar.

## Enviar mensajes como servidor

Abre una tercera terminal de VS Code y ejecuta:

```powershell
python .\08_web_cliente.py --servidor
```

En el prompt `Servidor>`, escribe el mensaje y presiona Enter. El texto se difundirá a los clientes con el prefijo `Servidor:`. Escribe `/salir` para cerrar esta consola de envío; esto no detiene el contenedor.

## Detener la aplicación

- Para detener el servidor, presiona `Ctrl+C` en la terminal de `docker compose up`.
- También puedes ejecutar `docker compose down` desde otra terminal en la carpeta del proyecto.

## Archivos y puertos

- `08_web_servidor.py`: servidor TCP, difusión de mensajes y asignación de nombres.
- `08_web_cliente.py`: cliente de chat y consola para enviar mensajes como servidor.
- `docker-compose.yml`: ejecuta el servidor en Docker y publica los puertos.
- `8765`: conexiones de los clientes.
- `8766`: conexión de la consola de mensajes del servidor.

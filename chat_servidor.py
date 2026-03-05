import socket
import threading
import json
import datetime

# ─────────────────────────────────────────────
#  CONFIGURACIÓN
# ─────────────────────────────────────────────
HOST = '127.0.0.1'
PORT = 5555
MAX_HISTORIAL = 20   # Últimos N mensajes guardados
MAX_ALIAS_LEN = 20
MIN_ALIAS_LEN = 2
BUFFER = 4096

# ─────────────────────────────────────────────
#  PROTOCOLO DE MENSAJES
# ─────────────────────────────────────────────
# Prefijos que el servidor ENVÍA al cliente:
#   ALIAS              → solicita el alias
#   ALIAS_TAKEN        → alias ya en uso, pedir otro
#   ALIAS_INVALID      → alias inválido
#   ALIAS_OK           → alias aceptado, puede entrar
#   HISTORY:<json>     → historial de mensajes al conectarse
#   USERS:<u1,u2,...>  → lista actual de usuarios
#   MSG:<alias>|<hh:mm>|<texto>  → mensaje de chat
#   SYS:<texto>        → mensaje del sistema (entró/salió)
#   TYPING:<alias>     → alguien está escribiendo
#
# Prefijos que el servidor RECIBE del cliente:
#   MSG:<alias>|<hh:mm>|<texto>  → mensaje de chat
#   TYPING                       → está escribiendo
#   LEAVE                        → desconexión limpia

# ─────────────────────────────────────────────
#  ESTADO GLOBAL
# ─────────────────────────────────────────────
clientes: dict[socket.socket, str] = {}   # {socket: alias}
historial: list[str] = []                 # Últimos MAX_HISTORIAL mensajes codificados
lock = threading.Lock()

# ─────────────────────────────────────────────
#  UTILIDADES
# ─────────────────────────────────────────────
def timestamp_ahora() -> str:
    return datetime.datetime.now().strftime("%H:%M")


def log(texto: str):
    ahora = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[{ahora}] {texto}")


def enviar(cliente: socket.socket, mensaje: str):
    """Envía un mensaje UTF-8 a un cliente específico, ignorando errores."""
    try:
        cliente.send(mensaje.encode('utf-8'))
    except Exception:
        pass


def broadcast(mensaje: str, excluir: socket.socket | None = None):
    """Reenvía un mensaje a todos los clientes conectados, excepto al emisor."""
    with lock:
        lista = list(clientes.keys())
    for c in lista:
        if c != excluir:
            enviar(c, mensaje)


def broadcast_lista_usuarios():
    """Notifica a todos la lista actualizada de usuarios conectados."""
    with lock:
        nombres = list(clientes.values())
    payload = "USERS:" + ",".join(nombres)
    broadcast(payload)


def agregar_historial(msg_codificado: str):
    """Añade un mensaje al historial y mantiene el límite."""
    with lock:
        historial.append(msg_codificado)
        if len(historial) > MAX_HISTORIAL:
            historial.pop(0)


# ─────────────────────────────────────────────
#  LÓGICA DE CLIENTES
# ─────────────────────────────────────────────
def remover_cliente(cliente: socket.socket):
    """Limpia al cliente de la lista y notifica a los demás."""
    with lock:
        alias = clientes.pop(cliente, None)
    if alias is None:
        return
    try:
        cliente.close()
    except Exception:
        pass
    log(f"🔴 {alias} se ha desconectado. [{len(clientes)} conectados]")
    sys_msg = f"SYS:🔴 {alias} ha salido del chat."
    broadcast(sys_msg)
    broadcast_lista_usuarios()


def manejar_cliente(cliente: socket.socket):
    """Hilo dedicado a escuchar mensajes de un cliente concreto."""
    while True:
        try:
            datos = cliente.recv(BUFFER)
            if not datos:
                remover_cliente(cliente)
                break

            mensaje = datos.decode('utf-8').strip()

            if mensaje == 'TYPING':
                # Reenviar indicador de escritura a los demás
                with lock:
                    alias = clientes.get(cliente, '')
                if alias:
                    broadcast(f"TYPING:{alias}", excluir=cliente)

            elif mensaje == 'LEAVE':
                remover_cliente(cliente)
                break

            elif mensaje.startswith('MSG:'):
                # Guardamos en historial y retransmitimos
                agregar_historial(mensaje)
                broadcast(mensaje, excluir=cliente)

            # (mensajes no reconocidos se ignoran)

        except Exception:
            remover_cliente(cliente)
            break


def recibir_conexiones(servidor: socket.socket):
    """Bucle principal: acepta nuevas conexiones y negocia el alias."""
    log(f"🟢 Servidor iniciado en {HOST}:{PORT} — esperando conexiones...")
    while True:
        try:
            cliente, direccion = servidor.accept()
        except OSError:
            break  # El servidor fue cerrado

        log(f"⚡ Nueva conexión desde {direccion}")

        # ── Negociación de alias ──────────────────
        alias_aceptado = False
        while not alias_aceptado:
            enviar(cliente, 'ALIAS')
            try:
                raw = cliente.recv(BUFFER)
                if not raw:
                    cliente.close()
                    break
                alias = raw.decode('utf-8').strip()
            except Exception:
                cliente.close()
                break

            # Validación
            if len(alias) < MIN_ALIAS_LEN or len(alias) > MAX_ALIAS_LEN or not alias.replace(' ', ''):
                enviar(cliente, 'ALIAS_INVALID')
                continue

            with lock:
                ya_existe = alias in clientes.values()

            if ya_existe:
                log(f"  ⚠ Alias '{alias}' rechazado (duplicado)")
                enviar(cliente, 'ALIAS_TAKEN')
                continue

            # Alias válido y único → registrar
            with lock:
                clientes[cliente] = alias
            alias_aceptado = True

        if not alias_aceptado:
            continue

        log(f"✅ '{alias}' aceptado. [{len(clientes)} conectados]")

        # ── Enviar historial ──────────────────────
        with lock:
            hist_copia = list(historial)
        if hist_copia:
            payload_hist = "HISTORY:" + json.dumps(hist_copia, ensure_ascii=False)
            enviar(cliente, payload_hist)

        # ── Bienvenida al resto ───────────────────
        sys_bienvenida = f"SYS:🟢 {alias} se ha unido al chat."
        broadcast(sys_bienvenida, excluir=cliente)

        # ── Confirmar al nuevo cliente y mandar lista ─
        enviar(cliente, f"SYS:✅ Conectado como '{alias}'. ¡Bienvenido!")
        broadcast_lista_usuarios()

        # ── Hilo de escucha ───────────────────────
        hilo = threading.Thread(target=manejar_cliente, args=(cliente,), daemon=True)
        hilo.start()


# ─────────────────────────────────────────────
#  ARRANQUE
# ─────────────────────────────────────────────
if __name__ == "__main__":
    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    servidor.bind((HOST, PORT))
    servidor.listen()

    try:
        recibir_conexiones(servidor)
    except KeyboardInterrupt:
        log("⛔ Servidor detenido por el usuario.")
    finally:
        servidor.close()

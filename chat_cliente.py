from __future__ import annotations
import customtkinter as ctk  # type: ignore[import]
import socket
import threading
import json
import datetime
import time
from typing import Optional, cast

# ─────────────────────────────────────────────
#  CONFIGURACIÓN
# ─────────────────────────────────────────────
HOST = '127.0.0.1'
PORT = 5555
BUFFER = 4096
MAX_MSG_LEN = 300
MAX_ALIAS_LEN = 20
MIN_ALIAS_LEN = 2

# ─────────────────────────────────────────────
#  PALETA DE COLORES
# ─────────────────────────────────────────────
BG_PRINCIPAL    = "#0d1117"
BG_SIDEBAR      = "#161b22"
BG_HEADER       = "#161b22"
BG_BURBUJA_YO   = "#1d4ed8"   # Azul — mis mensajes
BG_BURBUJA_OTRO = "#1e293b"   # Gris pizarra — mensajes de otros
BG_ENTRADA      = "#1c2333"
BG_SYS          = "#0d1117"   # Para mensajes del sistema
COLOR_TEXTO     = "#e6edf3"
COLOR_TIMESTAMP = "#8b949e"
COLOR_ALIAS     = "#58a6ff"
COLOR_SYS       = "#8b949e"
COLOR_VERDE     = "#3fb950"
COLOR_ROJO      = "#f85149"
COLOR_ACENTO    = "#1d4ed8"
FUENTE_UI       = "Segoe UI"

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────
def timestamp_ahora() -> str:
    return datetime.datetime.now().strftime("%H:%M")


def color_avatar(alias: str) -> str:
    """Genera un color de avatar consistente para cada alias."""
    colores = ["#ef4444", "#f97316", "#eab308", "#22c55e",
               "#06b6d4", "#6366f1", "#a855f7", "#ec4899"]
    idx = sum(ord(c) for c in alias) % len(colores)
    return colores[idx]


# ─────────────────────────────────────────────
#  PANTALLA DE LOGIN
# ─────────────────────────────────────────────
class PantallaLogin(ctk.CTk):
    """Ventana de bienvenida/login antes de entrar al chat."""

    def __init__(self):
        super().__init__()
        self.alias_resultado: Optional[str] = None
        self.socket_resultado: Optional[socket.socket] = None

        self.title("NeonChat — Iniciar sesión")
        self.geometry("460x580")
        self.resizable(False, False)
        self.configure(fg_color=BG_PRINCIPAL)

        self._construir_ui()
        self.protocol("WM_DELETE_WINDOW", self.destroy)

    def _construir_ui(self):
        # ── Logo / Título ────────────────────────
        ctk.CTkLabel(
            self, text="💬", font=(FUENTE_UI, 64)
        ).pack(pady=(50, 0))

        ctk.CTkLabel(
            self, text="NeonChat",
            font=(FUENTE_UI, 36, "bold"),
            text_color=COLOR_ACENTO
        ).pack(pady=(8, 0))

        ctk.CTkLabel(
            self, text="Chat en tiempo real",
            font=(FUENTE_UI, 14),
            text_color=COLOR_TIMESTAMP
        ).pack(pady=(2, 40))

        # ── Formulario ───────────────────────────
        ctk.CTkLabel(
            self, text="Elige tu alias",
            font=(FUENTE_UI, 14, "bold"),
            text_color=COLOR_TEXTO
        ).pack(anchor="w", padx=60)

        self.entry_alias = ctk.CTkEntry(
            self,
            placeholder_text=f"Entre {MIN_ALIAS_LEN} y {MAX_ALIAS_LEN} caracteres...",
            font=(FUENTE_UI, 15),
            height=48,
            width=340,
            fg_color=BG_ENTRADA,
            border_color=COLOR_ACENTO,
            text_color=COLOR_TEXTO
        )
        self.entry_alias.pack(pady=(6, 8), padx=60)
        self.entry_alias.bind("<Return>", lambda _: self._intentar_conectar())

        self.lbl_error = ctk.CTkLabel(
            self, text="",
            font=(FUENTE_UI, 12),
            text_color=COLOR_ROJO
        )
        self.lbl_error.pack(pady=(0, 8))

        self.btn_conectar = ctk.CTkButton(
            self,
            text="Conectar",
            font=(FUENTE_UI, 15, "bold"),
            height=48,
            width=340,
            fg_color=COLOR_ACENTO,
            hover_color="#1e40af",
            command=self._intentar_conectar
        )
        self.btn_conectar.pack(pady=(0, 16), padx=60)

        ctk.CTkLabel(
            self,
            text=f"Servidor: {HOST}:{PORT}",
            font=(FUENTE_UI, 11),
            text_color=COLOR_TIMESTAMP
        ).pack()

    def _mostrar_error(self, texto: str):
        self.lbl_error.configure(text=texto)
        self.btn_conectar.configure(state="normal", text="Conectar")

    def _intentar_conectar(self):
        alias = self.entry_alias.get().strip()

        # Validación local
        if len(alias) < MIN_ALIAS_LEN:
            self._mostrar_error(f"El alias debe tener al menos {MIN_ALIAS_LEN} caracteres.")
            return
        if len(alias) > MAX_ALIAS_LEN:
            self._mostrar_error(f"El alias no puede tener más de {MAX_ALIAS_LEN} caracteres.")
            return

        self.btn_conectar.configure(state="disabled", text="Conectando...")
        self.lbl_error.configure(text="")

        # Conectar en hilo para no bloquear UI
        threading.Thread(target=self._conectar_servidor, args=(alias,), daemon=True).start()

    def _conectar_servidor(self, alias: str):
        sock: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.connect((HOST, PORT))
        except ConnectionRefusedError:
            self.after(0, self._mostrar_error, "❌ No hay servidor activo en este momento.")
            return

        resultado = self._negociar_alias(sock, alias)
        if resultado is None:
            return
        alias_final, msg_bienvenida = resultado
        self.alias_resultado = alias_final
        self.socket_resultado = sock
        self.after(0, self._abrir_chat, msg_bienvenida)

    def _negociar_alias(self, sock: socket.socket, alias: str) -> Optional[tuple[str, str]]:
        """Negocia el alias con el servidor. Retorna (alias_acepatdo, msg_bienvenida) o None si falla."""
        intentos: int = 0
        alias_actual: str = alias
        while True:
            try:
                dato: str = sock.recv(BUFFER).decode('utf-8').strip()
            except Exception:
                self.after(0, self._mostrar_error, "❌ Error de red durante la conexión.")
                sock.close()
                return None

            if dato == 'ALIAS':
                sock.send(alias_actual.encode('utf-8'))  # type: ignore[union-attr]
                intentos = intentos + 1  # type: ignore[operator]

            elif dato == 'ALIAS_TAKEN':
                alias_base: str = alias
                sufijo: str = str(intentos)
                alias_nuevo: str = alias_base + sufijo
                limite: int = MAX_ALIAS_LEN
                if len(alias_nuevo) > limite:
                    alias_nuevo = alias_nuevo[:limite]  # type: ignore[index]
                alias_actual = alias_nuevo
                self.after(0, self._mostrar_error,
                           f"Alias en uso. Probando con '{alias_actual}'...")

            elif dato == 'ALIAS_INVALID':
                self.after(0, self._mostrar_error, "❌ Alias inválido. Elige otro.")
                sock.close()
                return None

            elif dato.startswith('SYS:') and 'Conectado' in dato:
                msg: str = dato.removeprefix('SYS:')
                return alias_actual, msg

    def _abrir_chat(self, msg_bienvenida: str):
        self.withdraw()
        _sock = cast(socket.socket, self.socket_resultado)
        _alias = cast(str, self.alias_resultado)
        chat = VentanaChat(_sock, _alias, msg_bienvenida)
        chat.protocol("WM_DELETE_WINDOW", lambda: self._cerrar_todo(chat))
        chat.mainloop()

    def _cerrar_todo(self, ventana_chat):
        ventana_chat._cerrar_limpio()
        self.destroy()


# ─────────────────────────────────────────────
#  VENTANA PRINCIPAL DE CHAT
# ─────────────────────────────────────────────
class VentanaChat(ctk.CTk):

    def __init__(self, sock: socket.socket, alias: str, msg_bienvenida: str):
        super().__init__()
        self.sock = sock
        self.alias = alias
        self._conectado = True
        self._typing_timer: threading.Timer | None = None
        self._ultimo_typing_enviado = 0.0
        self._usuarios: list[str] = []

        self.title(f"NeonChat  —  {self.alias}")
        self.geometry("920x680")
        self.minsize(700, 500)
        self.configure(fg_color=BG_PRINCIPAL)

        self._construir_ui()
        self._mostrar_sistema(msg_bienvenida)

        # Hilo de recepción
        hilo = threading.Thread(target=self._recibir, daemon=True)
        hilo.start()

        self.protocol("WM_DELETE_WINDOW", self._cerrar_limpio)

    # ── Construcción de la UI ───────────────────
    def _construir_ui(self):
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._crear_header()
        self._crear_centro()
        self._crear_footer()

    def _crear_header(self):
        header = ctk.CTkFrame(self, height=60, fg_color=BG_HEADER, corner_radius=0)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        header.grid_columnconfigure(1, weight=1)

        # Icono + nombre
        ctk.CTkLabel(
            header, text="💬  NeonChat",
            font=(FUENTE_UI, 20, "bold"),
            text_color=COLOR_ACENTO
        ).grid(row=0, column=0, padx=20, pady=16, sticky="w")

        # Estado de conexión
        self.lbl_estado = ctk.CTkLabel(
            header, text="● Conectado",
            font=(FUENTE_UI, 13, "bold"),
            text_color=COLOR_VERDE
        )
        self.lbl_estado.grid(row=0, column=1, padx=20, sticky="e")

        # Contador de usuarios
        self.lbl_num_usuarios = ctk.CTkLabel(
            header, text="👥 1",
            font=(FUENTE_UI, 13),
            text_color=COLOR_TIMESTAMP
        )
        self.lbl_num_usuarios.grid(row=0, column=2, padx=(0, 20), sticky="e")

    def _crear_centro(self):
        centro = ctk.CTkFrame(self, fg_color="transparent")
        centro.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        centro.grid_rowconfigure(0, weight=1)
        centro.grid_columnconfigure(0, weight=1)

        # ── Área de mensajes (scroll) ─────────────
        self.scroll_chat = ctk.CTkScrollableFrame(
            centro,
            fg_color=BG_PRINCIPAL,
            corner_radius=0
        )
        self.scroll_chat.grid(row=0, column=0, sticky="nsew", padx=(12, 0), pady=12)
        self.scroll_chat.grid_columnconfigure(0, weight=1)

        # ── Sidebar de usuarios ───────────────────
        sidebar = ctk.CTkFrame(centro, width=190, fg_color=BG_SIDEBAR, corner_radius=0)
        sidebar.grid(row=0, column=1, sticky="nsew", padx=(0, 0), pady=0)
        sidebar.grid_propagate(False)

        ctk.CTkLabel(
            sidebar, text="En el chat",
            font=(FUENTE_UI, 13, "bold"),
            text_color=COLOR_TIMESTAMP
        ).pack(pady=(16, 8), padx=16, anchor="w")

        self.frame_usuarios = ctk.CTkScrollableFrame(
            sidebar, fg_color="transparent"
        )
        self.frame_usuarios.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        # ── Indicador "escribiendo..." ────────────
        self.lbl_typing = ctk.CTkLabel(
            self, text="",
            font=(FUENTE_UI, 12, "italic"),
            text_color=COLOR_TIMESTAMP
        )
        self.lbl_typing.grid(row=2, column=0, sticky="w", padx=20, pady=(0, 2))

    def _crear_footer(self):
        footer = ctk.CTkFrame(self, height=72, fg_color=BG_HEADER, corner_radius=0)
        footer.grid(row=3, column=0, sticky="ew")
        footer.grid_propagate(False)
        footer.grid_columnconfigure(0, weight=1)

        # Contador de caracteres
        self.lbl_chars = ctk.CTkLabel(
            footer, text=f"0 / {MAX_MSG_LEN}",
            font=(FUENTE_UI, 11),
            text_color=COLOR_TIMESTAMP
        )
        self.lbl_chars.grid(row=0, column=0, padx=(20, 0), pady=(8, 0), sticky="w")

        # Entry + botón enviar
        barra = ctk.CTkFrame(footer, fg_color="transparent")
        barra.grid(row=1, column=0, columnspan=2, padx=12, pady=(4, 10), sticky="ew")
        barra.grid_columnconfigure(0, weight=1)

        self.entry_msg = ctk.CTkEntry(
            barra,
            placeholder_text="Escribe un mensaje... (/salir para salir)",
            font=(FUENTE_UI, 14),
            height=44,
            fg_color=BG_ENTRADA,
            border_color="#30363d",
            text_color=COLOR_TEXTO
        )
        self.entry_msg.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.entry_msg.bind("<Return>", lambda _: self._enviar_mensaje())
        self.entry_msg.bind("<KeyRelease>", self._on_keyrelease)

        self.btn_enviar = ctk.CTkButton(
            barra,
            text="Enviar ➤",
            font=(FUENTE_UI, 14, "bold"),
            height=44,
            width=110,
            fg_color=COLOR_ACENTO,
            hover_color="#1e40af",
            command=self._enviar_mensaje
        )
        self.btn_enviar.grid(row=0, column=1)

    # ── Renderizado de mensajes ─────────────────
    def _mostrar_burbuja(self, alias: str, texto: str, hora: str, es_mio: bool):
        """Agrega una burbuja de mensaje al área de chat."""
        contenedor = ctk.CTkFrame(self.scroll_chat, fg_color="transparent")
        contenedor.pack(fill="x", padx=10, pady=3)

        lado = "e" if es_mio else "w"
        color_burbuja = BG_BURBUJA_YO if es_mio else BG_BURBUJA_OTRO
        color_av = color_avatar(alias)

        # Fila de alineación
        fila = ctk.CTkFrame(contenedor, fg_color="transparent")
        fila.pack(anchor=lado)

        if not es_mio:
            # Avatar a la izquierda
            av_letra = alias[0].upper()
            av = ctk.CTkLabel(
                fila, text=av_letra,
                font=(FUENTE_UI, 13, "bold"),
                fg_color=color_av,
                text_color="white",
                width=34, height=34,
                corner_radius=17
            )
            av.grid(row=0, column=0, rowspan=2, padx=(0, 6), sticky="n", pady=(2, 0))

        # Burbuja
        burbuja = ctk.CTkFrame(fila, fg_color=color_burbuja, corner_radius=14)
        col_burbuja = 1 if not es_mio else 0
        burbuja.grid(row=0, column=col_burbuja, sticky="nsew")

        if not es_mio:
            ctk.CTkLabel(
                burbuja, text=alias,
                font=(FUENTE_UI, 11, "bold"),
                text_color=COLOR_ALIAS
            ).pack(anchor="w", padx=12, pady=(8, 0))

        ctk.CTkLabel(
            burbuja,
            text=texto,
            font=(FUENTE_UI, 14),
            text_color=COLOR_TEXTO,
            wraplength=420,
            justify="left" if not es_mio else "right"
        ).pack(anchor="w" if not es_mio else "e", padx=12, pady=(4, 4))

        ctk.CTkLabel(
            burbuja, text=hora,
            font=(FUENTE_UI, 10),
            text_color=COLOR_TIMESTAMP
        ).pack(anchor="e", padx=12, pady=(0, 6))

        if es_mio:
            # Avatar a la derecha
            av_letra = alias[0].upper()
            av = ctk.CTkLabel(
                fila, text=av_letra,
                font=(FUENTE_UI, 13, "bold"),
                fg_color=color_av,
                text_color="white",
                width=34, height=34,
                corner_radius=17
            )
            av.grid(row=0, column=1, rowspan=2, padx=(6, 0), sticky="n", pady=(2, 0))

        self._scroll_al_final()

    def _mostrar_sistema(self, texto: str):
        """Muestra un mensaje de sistema (entrada/salida/info) centrado."""
        fila = ctk.CTkFrame(self.scroll_chat, fg_color="transparent")
        fila.pack(fill="x", pady=4)

        ctk.CTkLabel(
            fila,
            text=f"— {texto} —",
            font=(FUENTE_UI, 12, "italic"),
            text_color=COLOR_SYS
        ).pack(anchor="center")

        self._scroll_al_final()

    def _scroll_al_final(self):
        """Auto-scroll al final del área de mensajes."""
        self.after(80, lambda: self.scroll_chat._parent_canvas.yview_moveto(1.0))

    # ── Sidebar de usuarios ─────────────────────
    def _actualizar_usuarios(self, usuarios: list[str]):
        self._usuarios = usuarios
        # Limpiar widgets anteriores
        for w in self.frame_usuarios.winfo_children():
            w.destroy()

        for u in usuarios:
            color_av = color_avatar(u)
            fila = ctk.CTkFrame(self.frame_usuarios, fg_color="transparent")
            fila.pack(fill="x", padx=4, pady=3)

            ctk.CTkLabel(
                fila, text=u[0].upper(),
                font=(FUENTE_UI, 11, "bold"),
                fg_color=color_av,
                text_color="white",
                width=28, height=28,
                corner_radius=14
            ).pack(side="left", padx=(4, 8))

            ctk.CTkLabel(
                fila, text=u,
                font=(FUENTE_UI, 13),
                text_color=COLOR_TEXTO if u != self.alias else COLOR_ALIAS
            ).pack(side="left")

        self.lbl_num_usuarios.configure(text=f"👥 {len(usuarios)}")

    # ── Indicador "escribiendo..." ──────────────
    def _mostrar_typing(self, alias: str):
        self.lbl_typing.configure(text=f"✏️  {alias} está escribiendo...")
        if hasattr(self, '_typing_clear_timer') and self._typing_clear_timer:
            self._typing_clear_timer.cancel()
        self._typing_clear_timer = threading.Timer(3.0, self._limpiar_typing)
        self._typing_clear_timer.daemon = True
        self._typing_clear_timer.start()

    def _limpiar_typing(self):
        self.after(0, lambda: self.lbl_typing.configure(text=""))

    # ── Recepción de mensajes del servidor ──────
    def _recibir(self):
        """Hilo secundario: escucha permanentemente al servidor."""
        while self._conectado:
            try:
                datos = self.sock.recv(BUFFER)
                if not datos:
                    self._on_desconexion()
                    break
                self._procesar(datos.decode('utf-8'))
            except Exception:
                if self._conectado:
                    self._on_desconexion()
                break

    def _procesar(self, raw: str):
        """Decodifica el prefijo y despacha al handler correcto."""
        for linea in raw.strip().split('\n'):
            linea = linea.strip()
            if not linea:
                continue

            if linea.startswith("MSG:"):
                partes = linea.removeprefix("MSG:").split("|", 2)
                if len(partes) == 3:
                    alias_emisor, hora, texto = partes
                    es_mio = (alias_emisor == self.alias)
                    self.after(0, self._mostrar_burbuja, alias_emisor, texto, hora, es_mio)

            elif linea.startswith("SYS:"):
                self.after(0, self._mostrar_sistema, linea.removeprefix("SYS:"))

            elif linea.startswith("USERS:"):
                lista = [u for u in linea.removeprefix("USERS:").split(",") if u]
                self.after(0, self._actualizar_usuarios, lista)

            elif linea.startswith("HISTORY:"):
                try:
                    msgs = json.loads(linea.removeprefix("HISTORY:"))
                    self.after(0, self._cargar_historial, msgs)
                except Exception:
                    pass

            elif linea.startswith("TYPING:"):
                alias_typing = linea.removeprefix("TYPING:")
                if alias_typing != self.alias:
                    self.after(0, self._mostrar_typing, alias_typing)

    def _cargar_historial(self, msgs: list):
        """Muestra el historial de mensajes al conectarse."""
        self.after(0, self._mostrar_sistema, "── Historial de mensajes ──")
        for msg in msgs:
            if msg.startswith("MSG:"):
                partes = msg[4:].split("|", 2)
                if len(partes) == 3:
                    alias_emisor, hora, texto = partes
                    es_mio = (alias_emisor == self.alias)
                    self.after(0, self._mostrar_burbuja, alias_emisor, texto, hora, es_mio)
        self.after(0, self._mostrar_sistema, "── Fin del historial ──")

    def _on_desconexion(self):
        """Llamado cuando se pierde la conexión con el servidor."""
        self._conectado = False
        self.after(0, self.lbl_estado.configure,
                   {"text": "● Desconectado", "text_color": COLOR_ROJO})
        self.after(0, self._mostrar_sistema, "⚠ Conexión con el servidor perdida.")
        self.after(0, self.btn_enviar.configure, {"state": "disabled"})
        self.after(0, self.entry_msg.configure, {"state": "disabled"})

    # ── Envío de mensajes ───────────────────────
    def _on_keyrelease(self, event):
        texto = self.entry_msg.get()
        longitud = len(texto)

        # Contador de caracteres
        color = COLOR_ROJO if longitud > MAX_MSG_LEN else COLOR_TIMESTAMP
        self.lbl_chars.configure(text=f"{longitud} / {MAX_MSG_LEN}", text_color=color)

        # Señal de "escribiendo" con debounce (max 1 cada 3 s)
        ahora = time.time()
        if longitud > 0 and (ahora - self._ultimo_typing_enviado) > 3:
            self._ultimo_typing_enviado = ahora
            try:
                self.sock.send("TYPING".encode('utf-8'))
            except Exception:
                pass

    def _enviar_mensaje(self):
        if not self._conectado:
            return

        texto = self.entry_msg.get().strip()
        if not texto:
            return

        # Comando /salir
        if texto.lower() == "/salir":
            self._cerrar_limpio()
            return

        # Validar longitud
        if len(texto) > MAX_MSG_LEN:
            self._mostrar_sistema(f"⚠ Mensaje demasiado largo (máximo {MAX_MSG_LEN} caracteres).")
            return

        hora = timestamp_ahora()
        msg = f"MSG:{self.alias}|{hora}|{texto}"

        try:
            self.sock.send(msg.encode('utf-8'))
        except Exception:
            self._mostrar_sistema("⚠ No se pudo enviar el mensaje.")
            return

        # Mostramos nuestro propio mensaje sin esperar al servidor
        self._mostrar_burbuja(self.alias, texto, hora, es_mio=True)
        self.entry_msg.delete(0, "end")
        self.lbl_chars.configure(text=f"0 / {MAX_MSG_LEN}", text_color=COLOR_TIMESTAMP)

    # ── Cierre limpio ───────────────────────────
    def _cerrar_limpio(self):
        if self._conectado:
            self._conectado = False
            try:
                self.sock.send("LEAVE".encode('utf-8'))
            except Exception:
                pass
            try:
                self.sock.close()
            except Exception:
                pass
        self.destroy()


# ─────────────────────────────────────────────
#  ARRANQUE
# ─────────────────────────────────────────────
if __name__ == "__main__":
    login = PantallaLogin()
    login.mainloop()

# 💬 NeonChat — App de Chat en Tiempo Real

Aplicación de chat en tiempo real con interfaz gráfica moderna, construida en Python usando sockets TCP y `customtkinter`.

---

## 📸 Características

- **Mensajes en tiempo real** a través de sockets TCP
- **Interfaz gráfica** oscura y moderna con burbujas de chat
- **Avatares de colores** generados automáticamente por alias
- **Indicador "está escribiendo..."** con debounce
- **Historial de mensajes** (últimos 20) enviado al conectarse
- **Lista de usuarios** en tiempo real en la barra lateral
- **Negociación de alias** automática (agrega sufijo si el alias está en uso)
- **Cierre limpio** con notificación a todos los usuarios

---

## 🗂 Estructura del Proyecto

```
App de Chat en Tiempo Real/
├── chat_servidor.py   # Servidor TCP multihilo
└── chat_cliente.py    # Cliente con GUI (customtkinter)
```

---

## ⚙️ Requisitos

- Python **3.10+**
- Librería `customtkinter`

Instalar dependencias:

```bash
pip install customtkinter
```

---

## 🚀 Cómo Ejecutar

### 1. Iniciar el servidor

```bash
python chat_servidor.py
```

El servidor escucha en `127.0.0.1:5555` por defecto.

### 2. Iniciar el cliente (puede abrir varios)

```bash
python chat_cliente.py
```

Se abrirá una ventana de login. Escribe tu alias y presiona **Conectar**.

> ⚠️ El servidor debe estar corriendo **antes** de iniciar cualquier cliente.

---

## 🔌 Protocolo de Mensajes

| Prefijo             | Dirección        | Descripción                             |
|---------------------|------------------|-----------------------------------------|
| `ALIAS`             | Servidor → Cliente | Solicita el alias del usuario          |
| `ALIAS_OK`          | Servidor → Cliente | Alias aceptado                         |
| `ALIAS_TAKEN`       | Servidor → Cliente | Alias ya en uso                        |
| `ALIAS_INVALID`     | Servidor → Cliente | Alias inválido                         |
| `MSG:<alias>\|<hh:mm>\|<texto>` | Ambos | Mensaje de chat                  |
| `SYS:<texto>`       | Servidor → Cliente | Mensaje del sistema                   |
| `USERS:<u1,u2,...>` | Servidor → Cliente | Lista de usuarios conectados          |
| `HISTORY:<json>`    | Servidor → Cliente | Historial al conectarse               |
| `TYPING`            | Cliente → Servidor | Señal de "está escribiendo"          |
| `TYPING:<alias>`    | Servidor → Cliente | Reenvío del indicador de escritura   |
| `LEAVE`             | Cliente → Servidor | Desconexión limpia                   |

---

## 🛠 Configuración

Ambos archivos tienen constantes al inicio que puedes modificar:

| Constante       | Valor por defecto | Descripción                          |
|-----------------|-------------------|--------------------------------------|
| `HOST`          | `127.0.0.1`       | Dirección IP del servidor            |
| `PORT`          | `5555`            | Puerto TCP                           |
| `BUFFER`        | `4096`            | Tamaño del buffer de red (bytes)     |
| `MAX_HISTORIAL` | `20`              | Mensajes guardados en el servidor    |
| `MAX_MSG_LEN`   | `300`             | Longitud máxima de un mensaje        |
| `MAX_ALIAS_LEN` | `20`              | Longitud máxima del alias            |
| `MIN_ALIAS_LEN` | `2`               | Longitud mínima del alias            |

---

## 💡 Uso

- Escribe tu mensaje y presiona **Enter** o el botón **Enviar ➤**
- El contador de caracteres te indica cuántos has usado (`0 / 300`)
- Escribe `/salir` para desconectarte limpiamente
- La barra lateral muestra quién está conectado en este momento

---

## 📄 Licencia

Proyecto personal de aprendizaje. Libre de usar y modificar.

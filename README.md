# 🎵 Argent Music Player

<div align="center">

![Version](https://img.shields.io/badge/version-1.1.0-blue?style=flat-square)
![Platform](https://img.shields.io/badge/platform-Linux-lightgrey?style=flat-square&logo=linux)
![Python](https://img.shields.io/badge/python-3.10%2B-yellow?style=flat-square&logo=python)
![GTK](https://img.shields.io/badge/GTK-4.0-green?style=flat-square)
![License](https://img.shields.io/badge/license-GPL--3.0-orange?style=flat-square)

**Reproductor de música local para Linux**
GTK4 + libadwaita + GStreamer + SQLite

</div>

---

## ✨ Características

| Función | Descripción |
|---|---|
| 🎨 **Color dinámico** | La interfaz adopta el color dominante de la portada del álbum en reproducción |
| 🗄️ **Biblioteca SQLite** | Indexado persistente — carga instantánea sin re-escanear en cada inicio |
| 📝 **Letras sincronizadas** | Letras LRC con scroll automático, desde archivo local o lrclib.net |
| 🎛️ **Ecualizador 10 bandas** | 8 presets incluidos (Rock, Pop, Bass Boost, Clásica, Electrónica, etc.) |
| 🔀 **Fundido entre canciones** | Crossfade configurable de 0 a 10 segundos |
| 📋 **Colas múltiples** | Tres colas de reproducción independientes (Q1, Q2, Q3) |
| 🏷️ **Editor de etiquetas** | Edita título, artista, álbum, género, número de pista y portada |
| 📁 **Vista de carpetas** | Explorador en árbol de todas las carpetas indexadas |
| 🎼 **Listas M3U** | Importa y exporta colas en formato `.m3u` estándar |
| 🪟 **Mini reproductor** | Ventana compacta flotante con portada, controles y progreso |
| 📡 **MPRIS2** | Integración con teclas multimedia y paneles del escritorio |
| 🌙 **Tema adaptable** | Sigue el tema del sistema (claro/oscuro) con botón manual |

### Formatos soportados

`MP3` · `FLAC` · `OGG` · `Opus` · `M4A` · `AAC` · `WAV` · `WMA` · `APE` · `WV`

---

## 📦 Instalación

### Opción A — Paquete .deb (recomendado en Debian/Ubuntu y derivados)

```bash
sudo dpkg -i argent-music-player_1.1.0_all.deb
sudo apt-get install -f   # si faltan dependencias
```

### Opción B — AppImage portable

```bash
chmod +x argent-music-player_1.1.0_x86_64.AppImage
./argent-music-player_1.1.0_x86_64.AppImage
```

Funciona en cualquier distribución Linux compatible con x86_64, sin necesidad de instalar dependencias por separado.

### Opción C — Desde el código fuente

**1. Instalar dependencias del sistema:**

```bash
sudo apt install \
  python3-gi python3-gi-cairo \
  gir1.2-gtk-4.0 gir1.2-adw-1 \
  gir1.2-gstreamer-1.0 \
  gstreamer1.0-plugins-base \
  gstreamer1.0-plugins-good \
  gstreamer1.0-plugins-ugly \
  gstreamer1.0-libav \
  gstreamer1.0-plugins-bad \
  python3-mutagen
```

> `gstreamer1.0-plugins-bad` es necesario para el ecualizador de 10 bandas. Sin él, el reproductor funciona normalmente pero el EQ queda deshabilitado.

**2. Ejecutar:**

```bash
python3 argent_music_player.py
```

---

## 🚀 Uso rápido

1. Abrí el reproductor y hacé clic en el botón de carpeta (arriba a la izquierda)
2. Seleccioná tu carpeta de música — se indexa automáticamente
3. En los próximos inicios, la biblioteca carga al instante desde SQLite
4. Navegá por las vistas **Canciones / Álbumes / Artistas / Géneros / Carpetas** con la barra inferior

---

## 🎛️ Funciones detalladas

### 🎨 Color dinámico de portada
El reproductor extrae el color más vibrante de la portada en reproducción y lo aplica como acento en toda la interfaz: barra de progreso, botón de reproducción y resaltado de la fila activa. Se recalcula automáticamente al cambiar de canción y se ajusta según el tema claro u oscuro activo.

### 📝 Letras sincronizadas
Debajo de la portada hay un botón que alterna entre la carátula y el panel de letras. La búsqueda sigue este orden:
1. Archivo `.lrc` local junto al audio
2. [lrclib.net](https://lrclib.net) como respaldo online

La línea activa se resalta y hace scroll automático para mantenerse visible.

### 📋 Colas múltiples (Q1 / Q2 / Q3)
Tres colas de reproducción completamente independientes, cada una con su propio índice, shuffle y modo de repetición. El botón **+** agrega la canción actual a la cola siguiente sin interrumpir la reproducción.

### 🎛️ Ecualizador
Botón EQ en el panel del reproductor. 8 presets predefinidos y ajuste manual de cada banda en tiempo real.

### 🔀 Fundido entre canciones (Crossfade)
Configurable entre 0 y 10 segundos. Con valor 0 el fundido está desactivado. La siguiente canción comienza con fade-in mientras la actual hace fade-out.

### 📁 Vista de carpetas
Muestra todas las carpetas indexadas como árbol navegable, con la cantidad de canciones de cada una. Útil cuando la música está organizada en varias ubicaciones.

### 🎼 Listas M3U
- **Exportar** guarda la cola actual como `.m3u`, compatible con cualquier reproductor
- **Importar** carga un `.m3u` existente y reproduce las canciones encontradas, resolviendo rutas relativas y absolutas

### 🪟 Mini reproductor flotante
Ventana compacta que se mantiene visible sobre el escritorio con portada, título, artista, controles y barra de progreso. Ideal para usar mientras trabajás en otra cosa.

### 🏷️ Editor de etiquetas
Accesible con el botón de lápiz durante la reproducción. Guarda los cambios directamente en el archivo de audio y actualiza la base de datos sin necesidad de re-escanear.

### 📡 MPRIS2
Las teclas **Play/Pause**, **Siguiente** y **Anterior** del teclado funcionan automáticamente en GNOME, KDE Plasma, XFCE y LXDE. El reproductor también aparece en los paneles de audio del sistema.

---

## 📁 Estructura del proyecto

```
argent-music-player/
├── argent_music_player.py         # Aplicación principal
├── build_deb.sh                   # Genera el paquete .deb
├── build_appimage.sh              # Genera AppImage básico
├── build_appimage_portable.sh     # Genera AppImage con dependencias embebidas
└── README.md
```

---

## 🗃️ Datos de la aplicación

| Ruta | Contenido |
|---|---|
| `~/.local/share/argent-music-player/library.db` | Biblioteca SQLite |

Para forzar un re-escaneo completo:
```bash
rm ~/.local/share/argent-music-player/library.db
```

---

## 🛠️ Stack técnico

- **UI:** GTK 4 + libadwaita
- **Audio:** GStreamer (`playbin3`)
- **Tags:** Mutagen
- **Base de datos:** SQLite 3
- **Letras:** [lrclib.net](https://lrclib.net) API
- **Integración DE:** MPRIS2 / D-Bus
- **Empaquetado:** `.deb` y AppImage

---

## 🗺️ Roadmap

- [ ] Estadísticas de escucha
- [ ] Ecualizador con más presets personalizables
- [ ] Sincronización de biblioteca entre dispositivos
- [ ] Port a Rust + gtk4-rs

---

## 📄 Licencia

Distribuido bajo la licencia **GNU General Public License v3.0**.
Consultá el archivo [`LICENSE`](LICENSE) para más detalles.

---

<div align="center">

Hecho con ❤️ por **Gustavo**

</div>

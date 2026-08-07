# 🎵 OpenArgent Music Player

<div align="center">

![Version](https://img.shields.io/badge/version-1.0.1-blue?style=flat-square)
![Platform](https://img.shields.io/badge/platform-Linux-lightgrey?style=flat-square&logo=linux)
![Python](https://img.shields.io/badge/python-3.10%2B-yellow?style=flat-square&logo=python)
![GTK](https://img.shields.io/badge/GTK-4.0-green?style=flat-square)
![License](https://img.shields.io/badge/license-GPL--3.0-orange?style=flat-square)

**Reproductor de música local para Linux**
Parte de **OpenArgentOS**

</div>

---

## ✨ Características

| Módulo | Descripción |
|--------|-------------|
| 🎨 **Color dinámico** | La interfaz adopta el color dominante de la portada del álbum en reproducción |
| 🗄️ **Biblioteca SQLite** | Indexado persistente — carga instantánea sin re-escanear en cada inicio |
| 🎛️ **Ecualizador 10 bandas** | Con 8 presets incluidos (Rock, Pop, Bass Boost, Clásica, etc.) |
| 🔀 **Fundido entre canciones** | Crossfade configurable de 0 a 10 segundos |
| 📋 **Colas múltiples** | Tres colas de reproducción independientes (Q1, Q2, Q3) |
| 🏷️ **Editor de etiquetas** | Edita título, artista, álbum, género, número de pista y portada directamente |
| 📡 **MPRIS2** | Integración completa con teclas multimedia y paneles del escritorio |
| 🌙 **Tema adaptable** | Sigue el tema del sistema (claro/oscuro) con botón de alternancia manual |

### Formatos soportados

`MP3` · `FLAC` · `OGG` · `Opus` · `M4A` · `AAC` · `WAV` · `WMA` · `APE` · `WV`

---

## 📦 Instalación

### Opción A — Paquete .deb (recomendado)

```bash
# Descargar el .deb desde Releases
sudo dpkg -i openargent-music-player_1.0.1_all.deb

# Si faltan dependencias
sudo apt-get install -f
```

### Opción B — Desde el código fuente

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
  python3-mutagen \
  gstreamer1.0-plugins-bad
```

> `gstreamer1.0-plugins-bad` es necesario para el ecualizador de 10 bandas.
> Sin él el reproductor funciona normalmente pero el EQ queda deshabilitado.

**2. Ejecutar:**

```bash
git clone https://github.com/Tavo78ok/argent-music-player
cd argent-music-player
python3 argent_music_player.py
```

### Opción C — Construir el .deb manualmente

```bash
git clone https://github.com/Tavo78ok/argent-music-player
cd argent-music-player
bash build_deb.sh
sudo dpkg -i argent-music-player_1.0.1_all.deb
```

---

## 🚀 Uso rápido

1. Abre el reproductor y haz clic en el botón de carpeta (arriba a la izquierda)
2. Selecciona tu carpeta de música — se indexará automáticamente
3. En los próximos inicios, la biblioteca carga al instante desde SQLite
4. Navega por las vistas **Canciones / Álbumes / Artistas / Géneros** con la barra inferior

---

## 🎛️ Funciones detalladas

### 🎨 Color dinámico de portada
Cuando se reproduce una canción con portada embebida, el reproductor extrae el color más vibrante y lo aplica como acento en toda la interfaz: barra de progreso, botón de reproducción y resaltado de la fila activa. El color se recalcula automáticamente al cambiar de canción y se ajusta según el tema claro u oscuro activo.

### 📋 Colas múltiples (Q1 / Q2 / Q3)
Inspirado en Musicolet para Android. Cada cola es completamente independiente y mantiene su propio índice, estado de shuffle y modo de repetición. El botón **+** junto a las colas agrega la canción actual a la cola siguiente. Puedes cambiar de cola en cualquier momento sin interrumpir la reproducción.

### 🎛️ Ecualizador
Abre el ecualizador con el botón **EQ** en el panel del reproductor. Dispone de 8 presets predefinidos y ajuste manual de cada banda. Los cambios se aplican en tiempo real sin interrumpir la reproducción.

### 🔀 Fundido entre canciones (Crossfade)
Configurable entre 0 y 10 segundos. Con valor 0 el fundido está desactivado. Cuando quedan X segundos para que termine la canción actual, el siguiente tema comienza a sonar con un fade-in suave mientras el actual hace fade-out.

### 🏷️ Editor de etiquetas
Accesible con el botón de lápiz mientras hay una canción en reproducción. Guarda los cambios directamente en el archivo de audio (usando Mutagen) y actualiza la base de datos SQLite sin necesidad de re-escanear.

### 📡 MPRIS2
Registra la aplicación como `org.mpris.MediaPlayer2.ArgentMusicPlayer`. Las teclas **Play/Pause**, **Siguiente** y **Anterior** del teclado funcionan automáticamente en GNOME, KDE Plasma, XFCE y LXDE. El reproductor también aparece en los paneles de audio del sistema.

---

## 📁 Estructura del proyecto

```
argent-music-player/
├── argent_music_player.py      # Aplicación principal
├── build_deb.sh               # Script para generar el .deb
├── deb/
│   └── argent-music-player/
│       ├── DEBIAN/
│       │   ├── control        # Metadatos del paquete
│       │   └── postinst       # Script post-instalación
│       └── usr/
│           ├── bin/           # Launcher del sistema
│           └── share/
│               ├── applications/       # Entrada .desktop
│               ├── argent-music-player/ # Archivo principal
│               └── icons/              # Ícono de la app
└── README.md
```

---

## 🗃️ Datos de la aplicación

| Ruta | Contenido |
|------|-----------|
| `~/.local/share/argent-music-player/library.db` | Biblioteca SQLite |

Para forzar un re-escaneo completo de la biblioteca:
```bash
rm ~/.local/share/argent-music-player/library.db
```

---

## 🛠️ Stack técnico

- **UI:** GTK 4 + libadwaita
- **Audio:** GStreamer (`playbin3`)
- **Tags:** Mutagen
- **Base de datos:** SQLite 3
- **Integración DE:** MPRIS2 / D-Bus
- **Empaquetado:** Debian `.deb`

---

## 🗺️ Roadmap

- [ ] Letras de canciones (LRC sincronizado)
- [ ] Vista de carpetas como explorador
- [ ] Mini reproductor flotante
- [ ] Estadísticas de escucha
- [ ] Soporte para listas de reproducción `.m3u`
- [ ] Publicación en Flathub

---

## 📄 Licencia

Distribuido bajo la licencia **GNU General Public License v3.0**.
Consulta el archivo [`LICENSE`](LICENSE) para más detalles.

---

<div align="center">

Hecho con ❤️ por **Gustavo** ·   OpenArgentOS (https://github.com/Tavo78ok)

</div>

<img width="1440" height="900" alt="Captura de pantalla_20260421_045833" src="https://github.com/user-attachments/assets/eb4a7d4a-e2be-4bca-88d9-3ef09d682ea1" />


<img width="1440" height="900" alt="Captura de pantalla_20260421_045925" src="https://github.com/user-attachments/assets/a414c5d3-b5c3-4ec0-a45b-b50e8edc1615" />


<img width="1440" height="900" alt="Captura de pantalla_20260421_050001" src="https://github.com/user-attachments/assets/942afdd3-728f-4097-978e-4d5243c14d54" />


<img width="1440" height="900" alt="Captura de pantalla_20260421_050049" src="https://github.com/user-attachments/assets/34870dcd-18b9-433c-89a7-ee4bf880402c" />


<img width="1440" height="900" alt="Captura de pantalla_20260421_050114" src="https://github.com/user-attachments/assets/6d52db60-a9b0-4089-9bca-4e1f72a71bae" />






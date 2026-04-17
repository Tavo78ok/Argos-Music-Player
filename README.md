### ArgOS Music Player v1.0

Reproductor de musica local para ArgOS Platinum Edition.
GTK4 + libadwaita + GStreamer + SQLite

## Dependencias

```bash
sudo apt install \
  python3-gi python3-gi-cairo gir1.2-gtk-4.0 \
  gir1.2-adw-1 gir1.2-gstreamer-1.0 \
  gstreamer1.0-plugins-base gstreamer1.0-plugins-good \
  gstreamer1.0-plugins-ugly gstreamer1.0-libav \
  python3-mutagen \
  gstreamer1.0-plugins-bad   # Para el ecualizador
```

## Ejecutar

```bash
python3 argos_music_player.py
```

## Instalar como .deb

```bash
bash build_deb.sh
sudo dpkg -i argos-music-player_1.0.0_all.deb
```

## Modulos implementados v1.0

- [x] Motor GStreamer (playbin3) con gapless
- [x] Biblioteca SQLite persistente
- [x] 4 vistas: Canciones / Albums / Artistas / Generos
- [x] Colas multiples (Q1, Q2, Q3) independientes
- [x] Ecualizador 10 bandas con 8 presets
- [x] Fundido entre canciones (crossfade configurable 0-10s)
- [x] Editor de etiquetas integrado (title/artist/album/genre/track/cover)
- [x] MPRIS2 completo (teclas multimedia, integracion con DE)
- [x] Extraccion de portada MP3/FLAC/OGG/Opus/M4A
- [x] Busqueda en tiempo real
- [x] Shuffle y repeat (none/one/all)
- [x] Logica prev: reinicia si >3s, anterior si <3s
- [x] Packaging .deb

## Teclas multimedia (via MPRIS2)

Una vez instalado, las teclas Play/Pause, Next, Previous del
teclado funcionan automaticamente en GNOME, KDE, XFCE y LXDE.

<img width="1440" height="900" alt="Captura de pantalla de 2026-04-16 21-23-06" src="https://github.com/user-attachments/assets/e36f41b9-925e-4ed8-bf5d-1f60e40f0d14" />

<img width="1440" height="900" alt="Captura de pantalla de 2026-04-16 21-23-25" src="https://github.com/user-attachments/assets/cf345a30-5478-4798-a0ef-df986384f9ed" />

<img width="1440" height="900" alt="Captura de pantalla de 2026-04-16 21-23-40" src="https://github.com/user-attachments/assets/5ac1387e-1a8a-476e-93b9-2294de9174bd" />




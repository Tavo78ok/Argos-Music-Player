#!/bin/bash
set -e
DEB_ROOT="deb/argos-music-player"

# 1. Estructura de directorios (añadimos la carpeta para el lanzador)
echo "📁 Preparando carpetas..."
mkdir -p "$DEB_ROOT/DEBIAN"
mkdir -p "$DEB_ROOT/usr/share/argos-music-player"
mkdir -p "$DEB_ROOT/usr/share/icons/hicolor/scalable/apps"
mkdir -p "$DEB_ROOT/usr/share/applications"
mkdir -p "$DEB_ROOT/usr/bin"

# 2. Archivo de control
cat > "$DEB_ROOT/DEBIAN/control" << EOF
Package: argos-music-player
Version: 1.0.1
Section: utils
Priority: optional
Architecture: all
Maintainer: Tu Nombre <correo@ejemplo.com>
Description: Reproductor de música para el ecosistema Argos.
EOF

# 3. Lanzador del Menú (.desktop)
echo "📝 Creando lanzador para el menú..."
cat > "$DEB_ROOT/usr/share/applications/argos-music-player.desktop" << EOF
[Desktop Entry]
Name=Argos Music Player
Comment=Reproductor de música de Argos
Exec=argos-music-player
Icon=argos-music-player
Terminal=false
Type=Application
Categories=AudioVideo;Audio;Player;
Keywords=music;reproductor;argos;
EOF

# 4. Script ejecutable en /usr/bin
# Esto permite que el comando 'Exec' del .desktop funcione
cat > "$DEB_ROOT/usr/bin/argos-music-player" << EOF
#!/bin/bash
python3 /usr/share/argos-music-player/argos_music_player.py "\$@"
EOF
chmod +x "$DEB_ROOT/usr/bin/argos-music-player"

# 5. Copiar el código fuente e icono
cp argos_music_player.py "$DEB_ROOT/usr/share/argos-music-player/"

cat > "$DEB_ROOT/usr/share/icons/hicolor/scalable/apps/argos-music-player.svg" << 'SVGEOF'
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <circle cx="32" cy="32" r="30" fill="#1c71d8"/>
  <circle cx="32" cy="32" r="12" fill="white" opacity="0.9"/>
  <circle cx="32" cy="32" r="5" fill="#1c71d8"/>
  <path d="M32 8 L32 2 M32 62 L32 56 M8 32 L2 32 M62 32 L56 32" stroke="white" stroke-width="3" opacity="0.5"/>
</svg>
SVGEOF

# 6. Finalizar paquete
INSTALLED_SIZE=$(du -sk "$DEB_ROOT" | cut -f1)
echo "Installed-Size: $INSTALLED_SIZE" >> "$DEB_ROOT/DEBIAN/control"

dpkg-deb --build --root-owner-group "$DEB_ROOT" argos-music-player_1.0.1_all.deb
echo "✅ Paquete completo generado. ¡Ahora sí debería aparecer en el menú!"

#!/bin/bash
set -e

VERSION="1.1.0"
PKG="argos-music-player"
DEB_ROOT="deb/$PKG"

echo "▶ Preparando estructura .deb..."

# Directorios
mkdir -p "$DEB_ROOT/DEBIAN"
mkdir -p "$DEB_ROOT/usr/bin"
mkdir -p "$DEB_ROOT/usr/share/$PKG"
mkdir -p "$DEB_ROOT/usr/share/applications"
mkdir -p "$DEB_ROOT/usr/share/icons/hicolor/scalable/apps"
mkdir -p "$DEB_ROOT/usr/share/icons/hicolor/256x256/apps"
mkdir -p "$DEB_ROOT/usr/share/icons/hicolor/128x128/apps"
mkdir -p "$DEB_ROOT/usr/share/icons/hicolor/48x48/apps"

# ── Archivo principal
cp argos_music_player.py "$DEB_ROOT/usr/share/$PKG/"

# ── Launcher
cat > "$DEB_ROOT/usr/bin/$PKG" << 'EOF'
#!/bin/bash
exec python3 /usr/share/argos-music-player/argos_music_player.py "$@"
EOF
chmod 755 "$DEB_ROOT/usr/bin/$PKG"

# ── .desktop
cat > "$DEB_ROOT/usr/share/applications/$PKG.desktop" << 'EOF'
[Desktop Entry]
Name=ArgOS Music Player
GenericName=Reproductor de música
Comment=Reproductor de música local para ArgOS Platinum Edition
Exec=argos-music-player
Icon=argos-music-player
Terminal=false
Type=Application
Categories=AudioVideo;Audio;Music;Player;GTK;
MimeType=audio/mpeg;audio/flac;audio/ogg;audio/opus;audio/x-wav;audio/mp4;audio/x-m4a;
Keywords=music;audio;player;mp3;flac;opus;lrc;letras;
StartupWMClass=argos-music-player
StartupNotify=true
EOF

# ── Icono SVG
cat > "$DEB_ROOT/usr/share/icons/hicolor/scalable/apps/$PKG.svg" << 'EOF'
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <defs>
    <radialGradient id="bg" cx="50%" cy="40%" r="55%">
      <stop offset="0%" stop-color="#3584e4"/>
      <stop offset="100%" stop-color="#1a5fb4"/>
    </radialGradient>
  </defs>
  <circle cx="32" cy="32" r="31" fill="url(#bg)"/>
  <rect x="26" y="18" width="4" height="18" rx="2" fill="white"/>
  <rect x="34" y="14" width="4" height="18" rx="2" fill="white"/>
  <rect x="26" y="18" width="12" height="4" rx="2" fill="white"/>
  <ellipse cx="24" cy="37" rx="6" ry="4" fill="white"/>
  <ellipse cx="32" cy="33" rx="6" ry="4" fill="white"/>
</svg>
EOF

# ── Generar PNGs
echo "▶ Generando iconos PNG..."
SVG_SRC="$DEB_ROOT/usr/share/icons/hicolor/scalable/apps/$PKG.svg"

generate_png() {
    local size=$1
    local dest="$DEB_ROOT/usr/share/icons/hicolor/${size}x${size}/apps/$PKG.png"
    if command -v rsvg-convert &>/dev/null; then
        rsvg-convert -w $size -h $size "$SVG_SRC" -o "$dest"
    elif command -v inkscape &>/dev/null; then
        inkscape --export-type=png --export-width=$size --export-height=$size \
                 --export-filename="$dest" "$SVG_SRC" 2>/dev/null
    elif command -v convert &>/dev/null; then
        convert -background none -resize ${size}x${size} "$SVG_SRC" "$dest" 2>/dev/null
    else
        python3 -c "
try:
    import cairosvg
    cairosvg.svg2png(url='$SVG_SRC',write_to='$dest',output_width=$size,output_height=$size)
except: pass
" 2>/dev/null || echo "  ⚠ No se pudo generar PNG ${size}x${size}"
    fi
    [ -f "$dest" ] && echo "  ✓ PNG ${size}x${size}" || true
}

generate_png 256
generate_png 128
generate_png 48

# ── control
cat > "$DEB_ROOT/DEBIAN/control" << EOF
Package: $PKG
Version: $VERSION
Section: sound
Priority: optional
Architecture: all
Depends: python3 (>= 3.10),
         python3-gi,
         python3-gi-cairo,
         gir1.2-gtk-4.0,
         gir1.2-adw-1,
         gir1.2-gstreamer-1.0,
         gstreamer1.0-plugins-base,
         gstreamer1.0-plugins-good,
         gstreamer1.0-plugins-ugly,
         gstreamer1.0-libav,
         python3-mutagen
Recommends: gstreamer1.0-plugins-bad
Maintainer: Andrés <argos@platinum.edition>
Installed-Size: $(du -sk "$DEB_ROOT" | cut -f1)
Description: ArgOS Music Player
 Reproductor de música local para ArgOS Platinum Edition.
 Soporta MP3, FLAC, OGG, Opus, M4A y más formatos.
 .
 Funciones: ecualizador 10 bandas, fundido entre canciones,
 colas múltiples, editor de etiquetas, letras LRC sincronizadas,
 color dinámico de portada, vista de carpetas, listas M3U,
 mini reproductor flotante e integración MPRIS2.
EOF

# ── postinst
cat > "$DEB_ROOT/DEBIAN/postinst" << 'EOF'
#!/bin/bash
set -e
if command -v update-desktop-database &>/dev/null; then
    update-desktop-database -q /usr/share/applications || true
fi
if command -v gtk-update-icon-cache &>/dev/null; then
    gtk-update-icon-cache -qf /usr/share/icons/hicolor || true
fi
exit 0
EOF
chmod 755 "$DEB_ROOT/DEBIAN/postinst"

# ── postrm
cat > "$DEB_ROOT/DEBIAN/postrm" << 'EOF'
#!/bin/bash
set -e
if command -v update-desktop-database &>/dev/null; then
    update-desktop-database -q /usr/share/applications || true
fi
if command -v gtk-update-icon-cache &>/dev/null; then
    gtk-update-icon-cache -qf /usr/share/icons/hicolor || true
fi
exit 0
EOF
chmod 755 "$DEB_ROOT/DEBIAN/postrm"

# ── Construir
echo "▶ Construyendo paquete .deb..."
dpkg-deb --build --root-owner-group "$DEB_ROOT" "${PKG}_${VERSION}_all.deb"
echo ""
echo "✅ ${PKG}_${VERSION}_all.deb generado"
echo "   Instalar: sudo dpkg -i ${PKG}_${VERSION}_all.deb"

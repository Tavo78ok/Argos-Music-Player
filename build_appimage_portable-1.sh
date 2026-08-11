#!/bin/bash
# ══════════════════════════════════════════════════════════════════
# Argent Music Player — AppImage PORTABLE (con dependencias)
# IMPORTANTE: ejecutar en una máquina Debian que ya
# tenga instalado: python3-gi, gtk4, libadwaita, gstreamer, mutagen.
# El script copia esas librerías DENTRO del AppImage para que
# funcione en máquinas que no las tengan instaladas.
# ══════════════════════════════════════════════════════════════════
set -e

VERSION="1.1.0"
PKG="argent-music-player"
APP_DIR="AppDir"
ARCH=$(uname -m)

echo "▶ Verificando dependencias del sistema..."
PYVER=$(python3 -c "import sys;print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "  Python detectado: $PYVER"

for pkg in python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 gir1.2-gstreamer-1.0; do
    dpkg -s "$pkg" &>/dev/null && echo "  ✓ $pkg" || { echo "  ✗ falta $pkg — instalalo antes de continuar"; exit 1; }
done

echo "▶ Preparando AppDir..."
rm -rf "$APP_DIR"
mkdir -p "$APP_DIR/usr/bin"
mkdir -p "$APP_DIR/usr/lib"
mkdir -p "$APP_DIR/usr/lib/python3/dist-packages"
mkdir -p "$APP_DIR/usr/lib/girepository-1.0"
mkdir -p "$APP_DIR/usr/share/$PKG"
mkdir -p "$APP_DIR/usr/share/applications"
mkdir -p "$APP_DIR/usr/share/glib-2.0/schemas"
mkdir -p "$APP_DIR/usr/share/icons/hicolor/256x256/apps"

cp argent_music_player.py "$APP_DIR/usr/share/$PKG/"

# ── 1. Copiar intérprete Python real (no el symlink de /usr/bin/python3)
PYBIN=$(readlink -f "$(command -v python3)")
cp "$PYBIN" "$APP_DIR/usr/bin/python3"
echo "  ✓ Python binario copiado ($PYBIN)"

# ── 2. Copiar stdlib de Python
PYLIBDIR="/usr/lib/python$PYVER"
if [ -d "$PYLIBDIR" ]; then
    cp -r "$PYLIBDIR" "$APP_DIR/usr/lib/"
    echo "  ✓ stdlib Python copiada"
fi

# ── 3. Copiar site-packages relevantes (gi, mutagen, cairo)
SITE="/usr/lib/python3/dist-packages"
for mod in gi mutagen cairo gi_typelibs; do
    if [ -d "$SITE/$mod" ]; then
        cp -r "$SITE/$mod" "$APP_DIR/usr/lib/python3/dist-packages/"
        echo "  ✓ módulo $mod copiado"
    fi
done
# Copiar también archivos sueltos .py de mutagen si viene como paquete simple
find "$SITE" -maxdepth 1 -iname "mutagen*" -exec cp -r {} "$APP_DIR/usr/lib/python3/dist-packages/" \; 2>/dev/null || true

# ── 4. Copiar typelibs GObject Introspection necesarios
TYPELIB_DIR="/usr/lib/$(uname -m)-linux-gnu/girepository-1.0"
[ -d "$TYPELIB_DIR" ] || TYPELIB_DIR="/usr/lib/girepository-1.0"
if [ -d "$TYPELIB_DIR" ]; then
    cp "$TYPELIB_DIR"/Gtk-4.0.typelib "$APP_DIR/usr/lib/girepository-1.0/" 2>/dev/null || true
    cp "$TYPELIB_DIR"/Adw-1.typelib "$APP_DIR/usr/lib/girepository-1.0/" 2>/dev/null || true
    cp "$TYPELIB_DIR"/Gst*.typelib "$APP_DIR/usr/lib/girepository-1.0/" 2>/dev/null || true
    cp "$TYPELIB_DIR"/{GLib,GObject,Gio,GdkPixbuf,Gdk,Pango,PangoCairo,cairo,HarfBuzz,Graphene,Gsk,GModule}-*.typelib "$APP_DIR/usr/lib/girepository-1.0/" 2>/dev/null || true
    echo "  ✓ typelibs copiados ($(ls "$APP_DIR/usr/lib/girepository-1.0" | wc -l) archivos)"
fi

# ── 5. Copiar plugins de GStreamer
GST_PLUGIN_DIR="/usr/lib/$(uname -m)-linux-gnu/gstreamer-1.0"
if [ -d "$GST_PLUGIN_DIR" ]; then
    mkdir -p "$APP_DIR/usr/lib/gstreamer-1.0"
    cp -r "$GST_PLUGIN_DIR"/* "$APP_DIR/usr/lib/gstreamer-1.0/"
    echo "  ✓ plugins GStreamer copiados"
fi

# ── 6. Copiar esquemas GSettings compilados
[ -f /usr/share/glib-2.0/schemas/gschemas.compiled ] && \
    cp /usr/share/glib-2.0/schemas/gschemas.compiled "$APP_DIR/usr/share/glib-2.0/schemas/"

# ── 7. AppRun con todas las variables de entorno necesarias
cat > "$APP_DIR/AppRun" << 'EOF'
#!/bin/bash
HERE="$(dirname "$(readlink -f "${0}")")"
export LD_LIBRARY_PATH="$HERE/usr/lib:$HERE/usr/lib/$(uname -m)-linux-gnu:$LD_LIBRARY_PATH"
export GI_TYPELIB_PATH="$HERE/usr/lib/girepository-1.0"
export GST_PLUGIN_PATH="$HERE/usr/lib/gstreamer-1.0"
export GST_PLUGIN_SYSTEM_PATH=""
export GST_REGISTRY="/tmp/argent-gst-registry.bin"
export GSETTINGS_SCHEMA_DIR="$HERE/usr/share/glib-2.0/schemas"
export XDG_DATA_DIRS="$HERE/usr/share:$XDG_DATA_DIRS"
export PYTHONHOME="$HERE/usr"
export PYTHONPATH="$HERE/usr/lib/python3/dist-packages:$HERE/usr/lib/python3.$(python3 -c 'import sys;print(sys.version_info.minor)' 2>/dev/null || echo 12)"
exec "$HERE/usr/bin/python3" "$HERE/usr/share/argent-music-player/argent_music_player.py" "$@"
EOF
chmod +x "$APP_DIR/AppRun"

# ── 8. .desktop + icono
cat > "$APP_DIR/$PKG.desktop" << 'EOF'
[Desktop Entry]
Name=Argent Music Player
Comment=Reproductor de música local con letras sincronizadas y ecualizador
Exec=argent-music-player
Icon=argent-music-player
Terminal=false
Type=Application
Categories=AudioVideo;Audio;Music;Player;GTK;
StartupWMClass=argent-music-player
EOF
cp "$APP_DIR/$PKG.desktop" "$APP_DIR/usr/share/applications/"

cat > /tmp/oa-icon.svg << 'EOF'
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
<circle cx="32" cy="32" r="31" fill="#1a5fb4"/>
<rect x="26" y="18" width="4" height="18" rx="2" fill="white"/>
<rect x="34" y="14" width="4" height="18" rx="2" fill="white"/>
<rect x="26" y="18" width="12" height="4" rx="2" fill="white"/>
<ellipse cx="24" cy="37" rx="6" ry="4" fill="white"/>
<ellipse cx="32" cy="33" rx="6" ry="4" fill="white"/>
</svg>
EOF
PNG_DEST="$APP_DIR/usr/share/icons/hicolor/256x256/apps/$PKG.png"
echo "▶ Generando ícono..."
if command -v rsvg-convert &>/dev/null; then
    rsvg-convert -w 256 -h 256 /tmp/oa-icon.svg -o "$PNG_DEST" && echo "  ✓ vía rsvg-convert"
elif command -v inkscape &>/dev/null; then
    inkscape --export-type=png --export-width=256 --export-height=256 \
             --export-filename="$PNG_DEST" /tmp/oa-icon.svg 2>/dev/null && echo "  ✓ vía inkscape"
elif command -v convert &>/dev/null; then
    convert -background none -resize 256x256 /tmp/oa-icon.svg "$PNG_DEST" 2>/dev/null && echo "  ✓ vía imagemagick"
fi

# appimagetool EXIGE un ícono en la raíz del AppDir. Si ninguna herramienta
# de conversión SVG→PNG está disponible, generamos un PNG mínimo en Python
# puro (sin dependencias) para que el build nunca falle por esto.
if [ ! -f "$PNG_DEST" ]; then
    echo "  ⚠ Sin rsvg-convert/inkscape/imagemagick — generando ícono placeholder"
    python3 -c "
import struct, zlib
def make_png(w,h,color):
    def chunk(t,d): return struct.pack('>I',len(d))+t+d+struct.pack('>I',zlib.crc32(t+d)&0xffffffff)
    sig=b'\x89PNG\r\n\x1a\n'
    ihdr=chunk(b'IHDR',struct.pack('>IIBBBBB',w,h,8,2,0,0,0))
    r,g,b=color
    raw=b''.join(b'\x00'+bytes([r,g,b]*w) for _ in range(h))
    idat=chunk(b'IDAT',zlib.compress(raw))
    iend=chunk(b'IEND',b'')
    return sig+ihdr+idat+iend
open('$PNG_DEST','wb').write(make_png(256,256,(26,95,180)))
"
    [ -f "$PNG_DEST" ] && echo "  ✓ placeholder generado"
fi

# Copiar SIEMPRE a la raíz del AppDir (requisito estricto de appimagetool)
if [ -f "$PNG_DEST" ]; then
    cp "$PNG_DEST" "$APP_DIR/$PKG.png"
else
    echo "  ❌ No se pudo crear ningún ícono — el build va a fallar"
fi

# ── 9. appimagetool
if [ ! -f "appimagetool-x86_64.AppImage" ]; then
    echo "▶ Descargando appimagetool..."
    wget -q "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage"
    chmod +x appimagetool-x86_64.AppImage
fi

echo "▶ Construyendo AppImage portable (esto puede tardar, es pesado)..."
OUT_FILE="${PKG}_${VERSION}_${ARCH}.AppImage"

# appimagetool es en sí mismo un AppImage y necesita FUSE para "montarse".
# Muchas distros recientes (Debian 12+, Ubuntu 22.04+) ya no traen fuse2
# instalado por defecto, lo que hace que falle en silencio y deje sueltos
# los archivos del AppDir (AppRun, .desktop, icono) en vez del .AppImage final.
# --appimage-extract-and-run evita depender de FUSE.
if ARCH=$ARCH ./appimagetool-x86_64.AppImage "$APP_DIR" "$OUT_FILE" 2>/tmp/appimagetool.log; then
    : # OK primer intento
elif grep -qi "fuse\|dlopen" /tmp/appimagetool.log; then
    echo "  ⚠ FUSE no disponible, reintentando con --appimage-extract-and-run..."
    ARCH=$ARCH ./appimagetool-x86_64.AppImage --appimage-extract-and-run "$APP_DIR" "$OUT_FILE"
else
    echo "  ⚠ Reintentando..."
    cat /tmp/appimagetool.log
fi

if [ -f "$OUT_FILE" ]; then
    chmod +x "$OUT_FILE"
    SIZE=$(du -h "$OUT_FILE" | cut -f1)
    echo ""
    echo "✅ $OUT_FILE generado ($SIZE)"
    echo "   Este archivo SÍ es portable — probalo en otra PC sin las dependencias instaladas."
else
    echo ""
    echo "❌ No se pudo generar el AppImage. Detalle:"
    cat /tmp/appimagetool.log 2>/dev/null
    echo ""
    echo "   Solución habitual: instalar FUSE"
    echo "   sudo apt install libfuse2t64 || sudo apt install libfuse2"
fi

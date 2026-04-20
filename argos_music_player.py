#!/usr/bin/env python3
"""ArgOS Music Player v1.0.1 - GTK4 + libadwaita + GStreamer + SQLite"""

import os, sys, gi, threading, sqlite3, base64, struct, json
from mutagen import File as MutagenFile
from pathlib import Path

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Gst", "1.0")
from gi.repository import Gtk, Adw, Gst, GLib, Gio, GdkPixbuf, Gdk, Pango, GObject as GObj
GLib.set_prgname('argos-music-player')
GLib.set_application_name('Argos Music Player')

Gst.init(None)

SUPPORTED_FORMATS = {".mp3",".flac",".ogg",".opus",".m4a",".aac",".wav",".wma",".ape",".mpc",".wv"}
REPEAT_NONE, REPEAT_ONE, REPEAT_ALL = 0, 1, 2
DB_PATH   = os.path.expanduser("~/.local/share/argos-music-player/library.db")
CONF_PATH = os.path.expanduser("~/.local/share/argos-music-player/config.json")

EQ_BANDS = [29, 59, 119, 237, 474, 947, 1889, 3770, 7523, 15011]
EQ_PRESETS = {
    "Plano":       [0,0,0,0,0,0,0,0,0,0],
    "Bass Boost":  [6,5,4,2,0,0,0,0,0,0],
    "Treble":      [0,0,0,0,0,2,3,4,5,6],
    "Pop":         [-1,2,4,4,2,0,-1,-1,-1,-1],
    "Rock":        [4,3,2,0,-1,0,2,3,3,3],
    "Clasica":     [4,3,2,0,0,0,0,0,2,3],
    "Electronica": [4,3,0,-2,-1,2,3,3,2,3],
    "Acustica":    [3,2,1,0,0,0,1,2,2,2],
}

MPRIS2_XML = """<node>
  <interface name="org.mpris.MediaPlayer2">
    <method name="Raise"/><method name="Quit"/>
    <property name="CanQuit" type="b" access="read"/>
    <property name="CanRaise" type="b" access="read"/>
    <property name="HasTrackList" type="b" access="read"/>
    <property name="Identity" type="s" access="read"/>
    <property name="SupportedUriSchemes" type="as" access="read"/>
    <property name="SupportedMimeTypes" type="as" access="read"/>
  </interface>
  <interface name="org.mpris.MediaPlayer2.Player">
    <method name="Next"/><method name="Previous"/>
    <method name="Pause"/><method name="PlayPause"/>
    <method name="Stop"/><method name="Play"/>
    <method name="Seek"><arg type="x" direction="in"/></method>
    <method name="SetPosition"><arg type="o" direction="in"/><arg type="x" direction="in"/></method>
    <method name="OpenUri"><arg type="s" direction="in"/></method>
    <signal name="Seeked"><arg type="x"/></signal>
    <property name="PlaybackStatus" type="s" access="read"/>
    <property name="LoopStatus"     type="s" access="readwrite"/>
    <property name="Rate"           type="d" access="readwrite"/>
    <property name="Shuffle"        type="b" access="readwrite"/>
    <property name="Metadata"       type="a{sv}" access="read"/>
    <property name="Volume"         type="d" access="readwrite"/>
    <property name="Position"       type="x" access="read"/>
    <property name="MinimumRate"    type="d" access="read"/>
    <property name="MaximumRate"    type="d" access="read"/>
    <property name="CanGoNext"      type="b" access="read"/>
    <property name="CanGoPrevious"  type="b" access="read"/>
    <property name="CanPlay"        type="b" access="read"/>
    <property name="CanPause"       type="b" access="read"/>
    <property name="CanSeek"        type="b" access="read"/>
    <property name="CanControl"     type="b" access="read"/>
  </interface>
</node>"""

# ══ Song ═══════════════════════════════════════════════════════════════
class Song:
    def __init__(self, path, title="", artist="", album="", genre="", duration=0, tracknumber=0):
        self.path=path; self.title=title or Path(path).stem
        self.artist=artist or "Artista desconocido"
        self.album=album or "Album desconocido"
        self.genre=genre or ""; self.duration=duration; self.tracknumber=tracknumber
        self.cover=None; self._cover_loaded=False

    @classmethod
    def from_path(cls, path):
        s=cls(path); name=Path(path).stem
        try:
            ext=Path(path).suffix.lower()
            # Opus y OGG: leer tags Vorbis directamente (easy=True falla con estos)
            if ext in (".opus", ".ogg"):
                from mutagen.oggopus import OggOpus
                from mutagen.oggvorbis import OggVorbis
                try:
                    raw = OggOpus(path) if ext==".opus" else OggVorbis(path)
                    def vget(key, default):
                        # Vorbis comments: claves en minuscula
                        v = raw.tags.get(key) or raw.tags.get(key.upper())
                        return v[0] if v else default
                    s.title  = vget("title",  name)
                    s.artist = vget("artist", "Artista desconocido")
                    s.album  = vget("album",  "Album desconocido")
                    s.genre  = vget("genre",  "")
                    tr = vget("tracknumber", None)
                    if tr:
                        try: s.tracknumber=int(str(tr).split("/")[0])
                        except: pass
                    if hasattr(raw,"info") and hasattr(raw.info,"length"):
                        s.duration=int(raw.info.length)
                    return s
                except Exception as e:
                    pass  # caer al metodo general

            # Resto de formatos con easy=True
            audio=MutagenFile(path, easy=True)
            if audio is None: return s
            t=audio.get("title",[None])[0]; s.title=str(t) if t else name
            s.artist=str(audio.get("artist",["Artista desconocido"])[0])
            s.album =str(audio.get("album", ["Album desconocido"])[0])
            s.genre =str(audio.get("genre", [""])[0])
            tr=audio.get("tracknumber",[None])[0]
            if tr:
                try: s.tracknumber=int(str(tr).split("/")[0])
                except: pass
            if hasattr(audio,"info") and hasattr(audio.info,"length"):
                s.duration=int(audio.info.length)
        except: pass
        return s

    def load_cover(self):
        if self._cover_loaded: return
        self._cover_loaded=True
        try:
            raw=MutagenFile(self.path)
            if raw is None: return
            if hasattr(raw,"tags") and raw.tags:
                for k in raw.tags.keys():
                    if k.startswith("APIC"): self.cover=raw.tags[k].data; return
            if hasattr(raw,"pictures") and raw.pictures:
                self.cover=raw.pictures[0].data; return
            if hasattr(raw,"tags") and raw.tags and "covr" in raw.tags:
                self.cover=bytes(raw.tags["covr"][0]); return
            if hasattr(raw,"tags") and raw.tags:
                for k in ("metadata_block_picture","METADATA_BLOCK_PICTURE"):
                    if k in raw.tags:
                        data=base64.b64decode(raw.tags[k][0]); off=4
                        ml=struct.unpack(">I",data[off:off+4])[0]; off+=4+ml
                        dl=struct.unpack(">I",data[off:off+4])[0]; off+=4+dl+16
                        il=struct.unpack(">I",data[off:off+4])[0]; off+=4
                        self.cover=data[off:off+il]; return
        except: pass

    @property
    def display_title(self):
        return f"{self.tracknumber:02d}. {self.title}" if self.tracknumber else self.title
    @property
    def filename(self): return Path(self.path).stem
    @property
    def duration_str(self):
        m,s=divmod(self.duration,60); h,m=divmod(m,60)
        return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"

# ══ Database ════════════════════════════════════════════════════════════
class MusicDatabase:
    def __init__(self):
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        self.conn=sqlite3.connect(DB_PATH, check_same_thread=False)
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS songs(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT UNIQUE NOT NULL, title TEXT, artist TEXT,
                album TEXT, genre TEXT, duration INTEGER DEFAULT 0,
                tracknumber INTEGER DEFAULT 0, folder TEXT);
            CREATE INDEX IF NOT EXISTS idx_artist ON songs(artist);
            CREATE INDEX IF NOT EXISTS idx_album  ON songs(album);
            CREATE INDEX IF NOT EXISTS idx_genre  ON songs(genre);
            CREATE INDEX IF NOT EXISTS idx_folder ON songs(folder);
        """); self.conn.commit()

    def upsert(self, s, folder):
        self.conn.execute("""
            INSERT INTO songs(path,title,artist,album,genre,duration,tracknumber,folder)
            VALUES(?,?,?,?,?,?,?,?)
            ON CONFLICT(path) DO UPDATE SET
              title=excluded.title, artist=excluded.artist, album=excluded.album,
              genre=excluded.genre, duration=excluded.duration,
              tracknumber=excluded.tracknumber, folder=excluded.folder
        """,(s.path,s.title,s.artist,s.album,s.genre,s.duration,s.tracknumber,folder))

    def commit(self): self.conn.commit()

    def remove_missing(self, folder):
        rows=self.conn.execute("SELECT path FROM songs WHERE folder=?",(folder,)).fetchall()
        bad=[r[0] for r in rows if not os.path.exists(r[0])]
        if bad: self.conn.executemany("DELETE FROM songs WHERE path=?",[(p,) for p in bad]); self.conn.commit()

    def _rs(self, rows): return [Song(r[0],r[1],r[2],r[3],r[4],r[5],r[6]) for r in rows]

    def all_songs(self):
        return self._rs(self.conn.execute("""SELECT path,title,artist,album,genre,duration,tracknumber FROM songs
            ORDER BY artist COLLATE NOCASE,album COLLATE NOCASE,tracknumber,title COLLATE NOCASE""").fetchall())

    def songs_in_folder(self, folder):
        return self._rs(self.conn.execute("""SELECT path,title,artist,album,genre,duration,tracknumber FROM songs
            WHERE folder=? ORDER BY artist COLLATE NOCASE,album COLLATE NOCASE,tracknumber,title COLLATE NOCASE""",(folder,)).fetchall())

    def songs_by_artist(self, artist):
        return self._rs(self.conn.execute("""SELECT path,title,artist,album,genre,duration,tracknumber FROM songs
            WHERE artist=? ORDER BY album COLLATE NOCASE,tracknumber,title COLLATE NOCASE""",(artist,)).fetchall())

    def songs_by_album(self, album, artist):
        return self._rs(self.conn.execute("""SELECT path,title,artist,album,genre,duration,tracknumber FROM songs
            WHERE album=? AND artist=? ORDER BY tracknumber,title COLLATE NOCASE""",(album,artist)).fetchall())

    def songs_by_genre(self, genre):
        return self._rs(self.conn.execute("""SELECT path,title,artist,album,genre,duration,tracknumber FROM songs
            WHERE COALESCE(NULLIF(genre,''),'Sin genero')=?
            ORDER BY artist COLLATE NOCASE,title COLLATE NOCASE""",(genre,)).fetchall())

    def update_tags(self, path, title, artist, album, genre, tracknumber):
        self.conn.execute("""UPDATE songs SET title=?,artist=?,album=?,genre=?,tracknumber=?
            WHERE path=?""",(title,artist,album,genre,tracknumber,path)); self.conn.commit()

    def all_artists(self):
        return self.conn.execute("""SELECT artist,COUNT(*) FROM songs
            GROUP BY artist COLLATE NOCASE ORDER BY artist COLLATE NOCASE""").fetchall()

    def all_albums(self):
        return self.conn.execute("""SELECT album,artist,COUNT(*) FROM songs
            GROUP BY album COLLATE NOCASE,artist COLLATE NOCASE
            ORDER BY artist COLLATE NOCASE,album COLLATE NOCASE""").fetchall()

    def all_genres(self):
        return self.conn.execute("""SELECT COALESCE(NULLIF(genre,''),'Sin genero') as g,COUNT(*)
            FROM songs GROUP BY g ORDER BY g COLLATE NOCASE""").fetchall()

    def is_indexed(self, folder):
        return self.conn.execute("SELECT COUNT(*) FROM songs WHERE folder=?",(folder,)).fetchone()[0]>0

    def needs_rescan(self, folder):
        indexed=set(r[0] for r in self.conn.execute("SELECT path FROM songs WHERE folder=?",(folder,)).fetchall())
        for root,_,files in os.walk(folder):
            for f in files:
                if Path(f).suffix.lower() in SUPPORTED_FORMATS:
                    if os.path.join(root,f) not in indexed: return True
        return False
# ══ AudioEngine con EQ + Crossfade ═════════════════════════════════════
class AudioEngine:
    def __init__(self, on_eos, on_error, on_position):
        self.on_eos=on_eos; self.on_error=on_error; self.on_position=on_position
        self._vol=1.0; self._xfade_secs=0; self._xfading=False
        self._xfade_step=0; self._xfade_total=20

        # Dos players para crossfade
        self._players=[
            Gst.ElementFactory.make("playbin3","playerA"),
            Gst.ElementFactory.make("playbin3","playerB"),
        ]
        self._active=0  # indice del player activo

        # EQ en el player principal
        self.eq=Gst.ElementFactory.make("equalizer-10bands","eq")
        self.eq_available=self.eq is not None
        if self.eq_available:
            try: self._players[0].set_property("audio-filter",self.eq)
            except: self.eq_available=False

        # Bus para ambos players
        for p in self._players:
            bus=p.get_bus(); bus.add_signal_watch()
            bus.connect("message::error", lambda b,m,pl=p: self._on_err(m))
        # EOS solo en el activo
        self._players[0].get_bus().connect("message::eos", lambda b,m: GLib.idle_add(self.on_eos))
        self._players[1].get_bus().connect("message::eos", lambda b,m: GLib.idle_add(self.on_eos))

        GLib.timeout_add(500, self._poll)

    @property
    def player(self): return self._players[self._active]

    def load(self, path):
        self.player.set_state(Gst.State.NULL)
        self.player.set_property("uri", Gst.filename_to_uri(path))
        self.player.set_property("volume", self._vol)

    def play(self):  self.player.set_state(Gst.State.PLAYING)
    def pause(self): self.player.set_state(Gst.State.PAUSED)
    def stop(self):
        for p in self._players: p.set_state(Gst.State.NULL)

    def seek(self, s):
        self.player.seek_simple(Gst.Format.TIME,
            Gst.SeekFlags.FLUSH|Gst.SeekFlags.KEY_UNIT, int(s*Gst.SECOND))

    def set_volume(self, v):
        self._vol=v
        if not self._xfading: self.player.set_property("volume",v)

    def set_crossfade(self, secs): self._xfade_secs=secs

    def set_eq_band(self, band, gain):
        if self.eq_available and self.eq:
            self.eq.set_property(f"band{band}", float(gain))

    def load_next_for_xfade(self, path):
        if not self._xfade_secs or not path: return
        nxt=(self._active+1)%2
        self._players[nxt].set_state(Gst.State.NULL)
        self._players[nxt].set_property("uri", Gst.filename_to_uri(path))
        self._players[nxt].set_property("volume", 0.0)
        self._players[nxt].set_state(Gst.State.PLAYING)
        self._xfading=True; self._xfade_step=0
        GLib.timeout_add(50, self._xfade_tick)

    def _xfade_tick(self):
        if not self._xfading: return False
        self._xfade_step+=1
        prog=self._xfade_step/self._xfade_total
        nxt=(self._active+1)%2
        self._players[self._active].set_property("volume", self._vol*(1-prog))
        self._players[nxt].set_property("volume", self._vol*prog)
        if self._xfade_step>=self._xfade_total:
            self._players[self._active].set_state(Gst.State.NULL)
            self._active=nxt; self._xfading=False
            # Mover EQ al nuevo player activo
            if self.eq_available and self.eq:
                try: self.player.set_property("audio-filter", self.eq)
                except: pass
            return False
        return True

    def _on_err(self, msg):
        err,_=msg.parse_error(); GLib.idle_add(self.on_error, str(err))

    def _poll(self):
        GLib.idle_add(self.on_position, self.position, self.duration)
        return True

    @property
    def position(self):
        ok,p=self.player.query_position(Gst.Format.TIME); return p/Gst.SECOND if ok else 0.0
    @property
    def duration(self):
        ok,d=self.player.query_duration(Gst.Format.TIME); return d/Gst.SECOND if ok else 0.0
    @property
    def is_playing(self):
        _,s,_=self.player.get_state(0); return s==Gst.State.PLAYING

# ══ PlayQueue ══════════════════════════════════════════════════════════
class PlayQueue:
    def __init__(self, name="Q1"):
        self.name=name; self.songs=[]; self.index=-1
        self.shuffle=False; self.repeat=REPEAT_NONE; self._order=[]

    def set_songs(self, songs, start=0):
        self.songs=songs; self.index=start; self._build()

    def _build(self):
        import random
        self._order=list(range(len(self.songs)))
        if self.shuffle:
            random.shuffle(self._order)
            if self.index in self._order: self._order.remove(self.index)
            self._order.insert(0,self.index)

    @property
    def current(self): return self.songs[self.index] if 0<=self.index<len(self.songs) else None
    @property
    def count(self): return len(self.songs)

    def _p(self):
        try: return self._order.index(self.index)
        except: return -1

    def next(self):
        if not self.songs: return None
        if self.repeat==REPEAT_ONE: return self.current
        p=self._p()+1
        if p>=len(self._order):
            if self.repeat==REPEAT_ALL: p=0
            else: return None
        self.index=self._order[p]; return self.current

    def prev(self):
        if not self.songs: return None
        self.index=self._order[max(0,self._p()-1)]; return self.current

    def peek_next(self):
        if not self.songs: return None
        if self.repeat==REPEAT_ONE: return self.current
        p=self._p()+1
        if p>=len(self._order):
            if self.repeat==REPEAT_ALL: p=0
            else: return None
        return self.songs[self._order[p]]

    def add(self, song): self.songs.append(song); self._build()
    def toggle_shuffle(self): self.shuffle=not self.shuffle; self._build()
    def next_repeat(self): self.repeat=(self.repeat+1)%3; return self.repeat

# ══ MultiQueueManager ══════════════════════════════════════════════════
class MultiQueueManager:
    NUM_QUEUES=3
    def __init__(self):
        self.queues=[PlayQueue(f"Q{i+1}") for i in range(self.NUM_QUEUES)]
        self._active=0
        self._on_switch_cb=None

    @property
    def queue(self): return self.queues[self._active]
    @property
    def active_idx(self): return self._active

    def switch(self, idx):
        if 0<=idx<self.NUM_QUEUES:
            self._active=idx
            if self._on_switch_cb: self._on_switch_cb(idx)

    def on_switch(self, cb): self._on_switch_cb=cb

    def add_to_queue(self, idx, song):
        self.queues[idx].add(song)

    # Delegate PlayQueue methods to active queue
    @property
    def songs(self): return self.queue.songs
    @property
    def index(self): return self.queue.index
    @index.setter
    def index(self, v): self.queue.index=v
    @property
    def shuffle(self): return self.queue.shuffle
    @property
    def repeat(self): return self.queue.repeat
    @property
    def current(self): return self.queue.current
    def set_songs(self, s, i=0): self.queue.set_songs(s,i)
    def next(self): return self.queue.next()
    def prev(self): return self.queue.prev()
    def peek_next(self): return self.queue.peek_next()
    def toggle_shuffle(self): self.queue.toggle_shuffle()
    def next_repeat(self): return self.queue.next_repeat()

# ══ MPRIS2 Service ═════════════════════════════════════════════════════
class MPRIS2Service:
    def __init__(self, win):
        self.win=win; self._conn=None; self._reg_ids=[]
        try:
            self._conn=Gio.bus_get_sync(Gio.BusType.SESSION,None)
            Gio.bus_own_name_on_connection(
                self._conn,"org.mpris.MediaPlayer2.ArgOSMusicPlayer",
                Gio.BusNameOwnerFlags.NONE,None,None)
            node=Gio.DBusNodeInfo.new_for_xml(MPRIS2_XML)
            for iface in node.interfaces:
                rid=self._conn.register_object(
                    "/org/mpris/MediaPlayer2",iface,
                    self._method,self._get,self._set)
                self._reg_ids.append(rid)
        except Exception as e:
            print(f"MPRIS2: {e}")

    def _method(self,conn,sender,path,iface,method,params,inv):
        try:
            w=self.win
            if method=="Next":     GLib.idle_add(w._on_next)
            elif method=="Previous":GLib.idle_add(w._on_prev)
            elif method=="PlayPause":GLib.idle_add(w._on_play_pause)
            elif method=="Play":
                if not w.engine.is_playing: GLib.idle_add(w._on_play_pause)
            elif method=="Pause":
                if w.engine.is_playing: GLib.idle_add(w._on_play_pause)
            elif method=="Stop":   GLib.idle_add(w.engine.stop)
            elif method=="Raise":  GLib.idle_add(w.present)
            elif method=="Quit":   GLib.idle_add(w.get_application().quit)
            inv.return_value(None)
        except Exception as e:
            inv.return_dbus_error("org.mpris.MediaPlayer2.Error",str(e))

    def _get(self,conn,sender,path,iface,prop):
        w=self.win; s=w.mqm.current
        try:
            if iface=="org.mpris.MediaPlayer2":
                d={"CanQuit":GLib.Variant("b",True),"CanRaise":GLib.Variant("b",True),
                   "HasTrackList":GLib.Variant("b",False),
                   "Identity":GLib.Variant("s","ArgOS Music Player"),
                   "SupportedUriSchemes":GLib.Variant("as",["file"]),
                   "SupportedMimeTypes":GLib.Variant("as",["audio/mpeg","audio/flac","audio/ogg","audio/opus"])}
                return d.get(prop)
            if iface=="org.mpris.MediaPlayer2.Player":
                if prop=="PlaybackStatus":
                    st="Playing" if w.engine.is_playing else ("Paused" if s else "Stopped")
                    return GLib.Variant("s",st)
                if prop=="LoopStatus":
                    m=w.mqm.repeat
                    return GLib.Variant("s","Track" if m==REPEAT_ONE else "Playlist" if m==REPEAT_ALL else "None")
                if prop=="Rate": return GLib.Variant("d",1.0)
                if prop=="Shuffle": return GLib.Variant("b",w.mqm.shuffle)
                if prop=="Metadata":
                    meta={"mpris:trackid":GLib.Variant("o","/org/mpris/MediaPlayer2/TrackList/NoTrack")}
                    if s:
                        meta["xesam:title"] =GLib.Variant("s",s.title)
                        meta["xesam:artist"]=GLib.Variant("as",[s.artist])
                        meta["xesam:album"] =GLib.Variant("s",s.album)
                        meta["mpris:length"] =GLib.Variant("x",s.duration*1000000)
                    return GLib.Variant("a{sv}",meta)
                if prop=="Volume":   return GLib.Variant("d",w._vol.get_value())
                if prop=="Position": return GLib.Variant("x",int(w.engine.position*1000000))
                if prop in ("MinimumRate","MaximumRate"): return GLib.Variant("d",1.0)
                bools={"CanGoNext","CanGoPrevious","CanPlay","CanPause","CanSeek","CanControl"}
                if prop in bools: return GLib.Variant("b",True)
        except: pass
        return None

    def _set(self,conn,sender,path,iface,prop,value):
        w=self.win
        if prop=="Volume": GLib.idle_add(w._vol.set_value,value.get_double())
        return True

    def notify(self):
        if not self._conn: return
        try:
            props={"PlaybackStatus":self._get(None,None,None,"org.mpris.MediaPlayer2.Player","PlaybackStatus",None),
                   "Metadata":self._get(None,None,None,"org.mpris.MediaPlayer2.Player","Metadata",None)}
            self._conn.emit_signal(None,"/org/mpris/MediaPlayer2",
                "org.freedesktop.DBus.Properties","PropertiesChanged",
                GLib.Variant("(sa{sv}as)",("org.mpris.MediaPlayer2.Player",props,[])))
        except: pass
# ══ GObject wrappers ═══════════════════════════════════════════════════
class SongObject(GObj.Object):
    __gtype_name__="SongObject"
    def __init__(self,song,pos): super().__init__(); self.song=song; self.position=pos

class StrObj(GObj.Object):
    __gtype_name__="StrObj"
    def __init__(self,text,data=None): super().__init__(); self.text=text; self.data=data

# ══ TagEditorDialog ════════════════════════════════════════════════════
class TagEditorDialog(Adw.Dialog):
    def __init__(self, song, on_save, parent):
        super().__init__()
        self.song=song; self._on_save=on_save
        self.set_title("Editor de etiquetas")
        self.set_content_width(480); self.set_content_height(560)
        self._new_cover=None

        box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        hdr=Adw.HeaderBar()
        hdr.set_title_widget(Adw.WindowTitle(title="Editor de etiquetas",subtitle=song.filename))
        save_btn=Gtk.Button(label="Guardar"); save_btn.add_css_class("suggested-action")
        save_btn.connect("clicked",self._save); hdr.pack_end(save_btn)
        box.append(hdr)

        scroll=Gtk.ScrolledWindow(); scroll.set_vexpand(True)
        scroll.set_policy(Gtk.PolicyType.NEVER,Gtk.PolicyType.AUTOMATIC)
        inner=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=16)
        inner.set_margin_top(16); inner.set_margin_bottom(16)
        inner.set_margin_start(16); inner.set_margin_end(16)

        # Cover
        cover_box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8); cover_box.set_halign(Gtk.Align.CENTER)
        self._cover_pic=Gtk.Picture(); self._cover_pic.set_size_request(140,140)
        self._cover_pic.add_css_class("cover-art")
        self._cover_pic.set_content_fit(Gtk.ContentFit.COVER)
        song.load_cover()
        if song.cover:
            try:
                ld=GdkPixbuf.PixbufLoader(); ld.write(song.cover); ld.close()
                self._cover_pic.set_pixbuf(ld.get_pixbuf())
            except: pass
        ch_btn=Gtk.Button(label="Cambiar portada"); ch_btn.add_css_class("flat")
        ch_btn.connect("clicked",self._change_cover)
        cover_box.append(self._cover_pic); cover_box.append(ch_btn)
        inner.append(cover_box)

        # Fields usando Adw.PreferencesGroup
        grp=Adw.PreferencesGroup(title="Informacion")
        self._f_title  =self._row(grp,"Titulo",  song.title)
        self._f_artist =self._row(grp,"Artista",  song.artist)
        self._f_album  =self._row(grp,"Album",    song.album)
        self._f_genre  =self._row(grp,"Genero",   song.genre)
        self._f_track  =self._row(grp,"Num. pista",str(song.tracknumber) if song.tracknumber else "")
        inner.append(grp)

        # File info
        info_grp=Adw.PreferencesGroup(title="Archivo")
        path_row=Adw.ActionRow(title="Ruta",subtitle=song.path); info_grp.add(path_row)
        dur_row=Adw.ActionRow(title="Duracion",subtitle=song.duration_str); info_grp.add(dur_row)
        fmt_row=Adw.ActionRow(title="Formato",subtitle=Path(song.path).suffix.upper()[1:]); info_grp.add(fmt_row)
        inner.append(info_grp)

        scroll.set_child(inner); box.append(scroll)
        self.set_child(box); self.present(parent)

    def _row(self, grp, title, val):
        row=Adw.EntryRow(title=title); row.set_text(val); grp.add(row); return row

    def _change_cover(self, _):
        d=Gtk.FileDialog(); d.set_title("Seleccionar imagen")
        ff=Gtk.FileFilter(); ff.set_name("Imagenes"); ff.add_mime_type("image/jpeg"); ff.add_mime_type("image/png")
        filters=Gio.ListStore.new(Gtk.FileFilter); filters.append(ff); d.set_filters(filters)
        d.open(None,None,self._cover_chosen)

    def _cover_chosen(self, dialog, result):
        try:
            f=dialog.open_finish(result)
            if f:
                with open(f.get_path(),"rb") as fh: self._new_cover=fh.read()
                ld=GdkPixbuf.PixbufLoader(); ld.write(self._new_cover); ld.close()
                self._cover_pic.set_pixbuf(ld.get_pixbuf())
        except: pass

    def _save(self, _):
        title=self._f_title.get_text().strip()
        artist=self._f_artist.get_text().strip()
        album=self._f_album.get_text().strip()
        genre=self._f_genre.get_text().strip()
        try: track=int(self._f_track.get_text().strip() or "0")
        except: track=0
        try:
            audio=MutagenFile(self.song.path, easy=True)
            if audio is not None:
                audio["title"]  =[title]
                audio["artist"] =[artist]
                audio["album"]  =[album]
                audio["genre"]  =[genre]
                if track: audio["tracknumber"]=[str(track)]
                audio.save()
            # Actualizar objeto
            self.song.title=title; self.song.artist=artist
            self.song.album=album; self.song.genre=genre; self.song.tracknumber=track
            if self._new_cover: self.song.cover=self._new_cover; self.song._cover_loaded=True
            if self._on_save: self._on_save(self.song)
        except Exception as e:
            print(f"Tag save error: {e}")
        self.close()

# ══ EQDialog ═══════════════════════════════════════════════════════════
class EQDialog(Adw.Dialog):
    FREQ_LABELS=["29Hz","59Hz","119Hz","237Hz","474Hz","947Hz","1.9kHz","3.8kHz","7.5kHz","15kHz"]

    def __init__(self, engine, parent):
        super().__init__()
        self.engine=engine
        self.set_title("Ecualizador")
        self.set_content_width(520); self.set_content_height(380)
        self._sliders=[]

        box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        hdr=Adw.HeaderBar()
        hdr.set_title_widget(Adw.WindowTitle(title="Ecualizador 10 bandas"))
        box.append(hdr)

        if not engine.eq_available:
            lbl=Gtk.Label(label="Instala gstreamer1.0-plugins-bad para habilitar el ecualizador")
            lbl.set_wrap(True); lbl.set_margin_top(32); lbl.add_css_class("dim-label")
            box.append(lbl); self.set_child(box); self.present(parent); return

        # Presets
        pbox=Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,spacing=8)
        pbox.set_margin_start(16); pbox.set_margin_end(16); pbox.set_margin_top(12)
        plbl=Gtk.Label(label="Preset:"); plbl.add_css_class("dim-label")
        combo=Gtk.DropDown.new_from_strings(list(EQ_PRESETS.keys()))
        combo.connect("notify::selected",self._on_preset); combo.set_hexpand(True)
        pbox.append(plbl); pbox.append(combo); box.append(pbox)

        # Sliders
        eq_box=Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,spacing=4)
        eq_box.set_margin_start(12); eq_box.set_margin_end(12)
        eq_box.set_margin_top(12); eq_box.set_margin_bottom(16)
        eq_box.set_vexpand(True)

        for i,label in enumerate(self.FREQ_LABELS):
            col=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=4)
            col.set_hexpand(True); col.set_halign(Gtk.Align.CENTER)
            sl=Gtk.Scale.new_with_range(Gtk.Orientation.VERTICAL,-12,12,0.5)
            sl.set_draw_value(True); sl.set_vexpand(True)
            sl.set_inverted(True)
            sl.add_mark(0,Gtk.PositionType.RIGHT,"0")
            # Valor actual del EQ
            try: cur=engine.eq.get_property(f"band{i}") if engine.eq else 0.0
            except: cur=0.0
            sl.set_value(cur)
            sl.connect("value-changed",self._on_band,i)
            self._sliders.append(sl)
            lbl=Gtk.Label(label=label); lbl.add_css_class("caption"); lbl.add_css_class("dim-label")
            col.append(sl); col.append(lbl); eq_box.append(col)

        box.append(eq_box)
        # Reset
        rst=Gtk.Button(label="Restablecer"); rst.add_css_class("flat")
        rst.set_halign(Gtk.Align.CENTER); rst.set_margin_bottom(8)
        rst.connect("clicked",self._reset); box.append(rst)
        self.set_child(box); self.present(parent)

    def _on_band(self, sl, band):
        self.engine.set_eq_band(band, sl.get_value())

    def _on_preset(self, combo, _):
        name=list(EQ_PRESETS.keys())[combo.get_selected()]
        vals=EQ_PRESETS[name]
        for i,(sl,v) in enumerate(zip(self._sliders,vals)):
            sl.set_value(v); self.engine.set_eq_band(i,v)

    def _reset(self, _):
        for i,sl in enumerate(self._sliders):
            sl.set_value(0); self.engine.set_eq_band(i,0)

# ══ XfadeSettingsDialog ════════════════════════════════════════════════
class XfadeDialog(Adw.Dialog):
    def __init__(self, engine, parent):
        super().__init__()
        self.engine=engine
        self.set_title("Fundido entre canciones")
        self.set_content_width(360); self.set_content_height(200)
        box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        hdr=Adw.HeaderBar()
        hdr.set_title_widget(Adw.WindowTitle(title="Fundido (Crossfade)"))
        box.append(hdr)
        inner=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=16)
        inner.set_margin_top(20); inner.set_margin_bottom(20)
        inner.set_margin_start(20); inner.set_margin_end(20)
        lbl=Gtk.Label(label="Duracion del fundido entre canciones:")
        lbl.set_halign(Gtk.Align.START)
        sl=Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL,0,10,0.5)
        sl.set_value(engine._xfade_secs); sl.set_draw_value(True)
        sl.add_mark(0,Gtk.PositionType.BOTTOM,"Off")
        sl.add_mark(3,Gtk.PositionType.BOTTOM,"3s")
        sl.add_mark(6,Gtk.PositionType.BOTTOM,"6s")
        sl.add_mark(10,Gtk.PositionType.BOTTOM,"10s")
        sl.connect("value-changed",lambda sc: engine.set_crossfade(sc.get_value()))
        inner.append(lbl); inner.append(sl)
        note=Gtk.Label(label="0 = desactivado")
        note.add_css_class("dim-label"); note.add_css_class("caption")
        inner.append(note); box.append(inner)
        self.set_child(box); self.present(parent)
# ══ Main Window ════════════════════════════════════════════════════════
class ArgOSMusicPlayer(Adw.ApplicationWindow):
    def __init__(self,app):
        super().__init__(application=app)
        self.set_title("ArgOS Music Player")
        self.set_default_size(1080,700); self.set_size_request(720,520)
        self.db=MusicDatabase()
        self.mqm=MultiQueueManager()
        self.engine=AudioEngine(self._on_eos,self._on_eng_err,self._update_pos)
        self.mpris=MPRIS2Service(self)
        self._seeking=False; self._folder=None
        self._build_ui(); self._apply_css()
        songs=self.db.all_songs()
        if songs: self._populate(songs)

    def _apply_css(self):
        p=Gtk.CssProvider()
        p.load_from_data(b"""
        .cover-art{border-radius:12px}
        .cover-ph{border-radius:12px;background-color:alpha(@accent_color,.1)}
        .song-title{font-size:17px;font-weight:bold}
        .song-artist{font-size:13px}
        .row-title{font-size:13px;font-weight:500}
        .row-sub{font-size:11px}
        .time-label{font-size:12px;font-variant-numeric:tabular-nums}
        .active-row{background-color:alpha(@accent_color,.15);border-radius:8px}
        .lib-title{font-size:13px;font-weight:600}
        .lib-sub{font-size:11px}
        .queue-btn{font-size:11px;font-weight:600;min-width:32px;padding:2px 6px}
        .queue-btn-active{background-color:alpha(@accent_color,.2)}
        """)
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(),p,Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def _build_ui(self):
        hdr=Adw.HeaderBar()
        self._wtitle=Adw.WindowTitle(title="ArgOS Music Player",subtitle="Biblioteca")
        hdr.set_title_widget(self._wtitle)
        ob=Gtk.Button(icon_name="document-open-symbolic",tooltip_text="Abrir carpeta")
        ob.connect("clicked",self._on_open); hdr.pack_start(ob)
        self._sbtn=Gtk.ToggleButton(icon_name="system-search-symbolic",tooltip_text="Buscar")
        self._sbtn.connect("toggled",self._on_search_toggled); hdr.pack_end(self._sbtn)
        mb=Gtk.MenuButton(icon_name="open-menu-symbolic"); mb.set_menu_model(self._build_menu()); hdr.pack_end(mb)

        self._sbar=Gtk.SearchBar()
        self._sentry=Gtk.SearchEntry(placeholder_text="Buscar en la biblioteca...")
        self._sentry.connect("search-changed",self._on_search_changed)
        self._sbar.set_child(self._sentry); self._sbar.connect_entry(self._sentry)
        self._sbtn.bind_property("active",self._sbar,"search-mode-enabled",GObj.BindingFlags.BIDIRECTIONAL)

        root=Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        root.append(hdr); root.append(self._sbar)
        paned=Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        paned.set_vexpand(True); paned.set_position(315)
        paned.set_start_child(self._build_player()); paned.set_shrink_start_child(False); paned.set_resize_start_child(False)
        paned.set_end_child(self._build_library())
        root.append(paned); self.set_content(root)

    def _build_player(self):
        box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.set_size_request(295,-1); box.add_css_class("background")
        inner=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=12)
        inner.set_margin_top(18); inner.set_margin_bottom(6)
        inner.set_margin_start(14); inner.set_margin_end(14); inner.set_vexpand(True)

        # Cover
        self._cstack=Gtk.Stack(); self._cstack.set_size_request(190,190); self._cstack.set_halign(Gtk.Align.CENTER)
        ph=Gtk.Box(); ph.add_css_class("cover-ph"); ph.set_size_request(190,190)
        ic=Gtk.Image.new_from_icon_name("audio-x-generic-symbolic")
        ic.set_pixel_size(56); ic.set_opacity(0.3); ic.set_hexpand(True); ic.set_valign(Gtk.Align.CENTER)
        ph.append(ic); self._cstack.add_named(ph,"ph")
        self._cimg=Gtk.Picture(); self._cimg.set_size_request(190,190)
        self._cimg.add_css_class("cover-art"); self._cimg.set_content_fit(Gtk.ContentFit.COVER)
        self._cstack.add_named(self._cimg,"cover"); inner.append(self._cstack)

        # Info
        info=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=2); info.set_halign(Gtk.Align.CENTER)
        self._lt=Gtk.Label(label="Sin reproduccion"); self._lt.add_css_class("song-title")
        self._lt.set_ellipsize(Pango.EllipsizeMode.END); self._lt.set_max_width_chars(22)
        self._lar=Gtk.Label(label="—"); self._lar.add_css_class("song-artist"); self._lar.add_css_class("dim-label")
        self._lar.set_ellipsize(Pango.EllipsizeMode.END); self._lar.set_max_width_chars(26)
        self._lab=Gtk.Label(label=""); self._lab.add_css_class("caption"); self._lab.add_css_class("dim-label")
        self._lab.set_ellipsize(Pango.EllipsizeMode.END); self._lab.set_max_width_chars(26)
        info.append(self._lt); info.append(self._lar); info.append(self._lab); inner.append(info)

        # Seek
        sb=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=2)
        self._seek=Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL,0,1,0.01)
        self._seek.set_draw_value(False); self._seek.set_hexpand(True)
        self._seek.connect("change-value",self._on_seek_change)
        sg=Gtk.GestureClick.new()
        sg.connect("pressed",lambda *_: setattr(self,"_seeking",True))
        sg.connect("released",self._on_seek_rel); self._seek.add_controller(sg)
        tr=Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self._lpos=Gtk.Label(label="0:00"); self._lpos.add_css_class("time-label")
        self._ldur=Gtk.Label(label="0:00"); self._ldur.add_css_class("time-label")
        sp=Gtk.Label(); sp.set_hexpand(True)
        tr.append(self._lpos); tr.append(sp); tr.append(self._ldur)
        sb.append(self._seek); sb.append(tr); inner.append(sb)

        # Controls
        ctrl=Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,spacing=4); ctrl.set_halign(Gtk.Align.CENTER)
        self._bsh=Gtk.ToggleButton(icon_name="media-playlist-shuffle-symbolic",tooltip_text="Aleatorio")
        self._bsh.connect("toggled",lambda b: self.mqm.toggle_shuffle())
        bpv=Gtk.Button(icon_name="media-skip-backward-symbolic",tooltip_text="Anterior"); bpv.connect("clicked",self._on_prev)
        self._bpl=Gtk.Button(icon_name="media-playback-start-symbolic")
        self._bpl.add_css_class("suggested-action"); self._bpl.add_css_class("circular")
        self._bpl.connect("clicked",self._on_play_pause)
        bnx=Gtk.Button(icon_name="media-skip-forward-symbolic",tooltip_text="Siguiente"); bnx.connect("clicked",self._on_next)
        self._brp=Gtk.Button(icon_name="media-playlist-repeat-symbolic",tooltip_text="Repetir"); self._brp.connect("clicked",self._on_repeat)
        for w in (self._bsh,bpv,self._bpl,bnx,self._brp): w.add_css_class("flat"); ctrl.append(w)
        inner.append(ctrl)

        # Volume
        vb=Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,spacing=6)
        self._vico=Gtk.Image.new_from_icon_name("audio-volume-medium-symbolic"); self._vico.set_pixel_size(16)
        self._vol=Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL,0,1,0.01)
        self._vol.set_value(1.0); self._vol.set_draw_value(False); self._vol.set_hexpand(True)
        self._vol.connect("value-changed",self._on_vol)
        vb.append(self._vico); vb.append(self._vol); inner.append(vb)

        # Multi-queue buttons
        qbox=Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,spacing=4)
        qbox.set_halign(Gtk.Align.CENTER)
        qlbl=Gtk.Label(label="Cola:"); qlbl.add_css_class("dim-label"); qlbl.add_css_class("caption")
        qbox.append(qlbl)
        self._qbtns=[]
        for i in range(MultiQueueManager.NUM_QUEUES):
            btn=Gtk.ToggleButton(label=f"Q{i+1}")
            btn.add_css_class("flat"); btn.add_css_class("queue-btn")
            btn.connect("toggled",self._on_queue_btn,i)
            self._qbtns.append(btn); qbox.append(btn)
        self._qbtns[0].set_active(True)
        # Queue add button
        qadd=Gtk.Button(icon_name="list-add-symbolic",tooltip_text="Agregar a cola")
        qadd.add_css_class("flat"); qadd.connect("clicked",self._on_add_to_queue); qbox.append(qadd)
        inner.append(qbox)

        # Extra tools row
        tools=Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,spacing=4); tools.set_halign(Gtk.Align.CENTER)
        eq_btn=Gtk.Button(icon_name="multimedia-equalizer-symbolic",tooltip_text="Ecualizador")
        eq_btn.add_css_class("flat"); eq_btn.connect("clicked",lambda _: EQDialog(self.engine,self))
        xf_btn=Gtk.Button(icon_name="media-record-symbolic",tooltip_text="Fundido entre canciones")
        xf_btn.add_css_class("flat"); xf_btn.connect("clicked",lambda _: XfadeDialog(self.engine,self))
        tag_btn=Gtk.Button(icon_name="document-edit-symbolic",tooltip_text="Editar etiquetas")
        tag_btn.add_css_class("flat"); tag_btn.connect("clicked",self._on_edit_tags)
        for w in (eq_btn,xf_btn,tag_btn): tools.append(w)
        inner.append(tools)

        # Status
        stb=Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,spacing=6); stb.set_halign(Gtk.Align.CENTER)
        self._spin=Gtk.Spinner(); self._spin.set_visible(False)
        self._lstat=Gtk.Label(label=""); self._lstat.add_css_class("caption"); self._lstat.add_css_class("dim-label")
        stb.append(self._spin); stb.append(self._lstat); inner.append(stb)
        box.append(inner); return box

    def _build_library(self):
        box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self._vstack=Adw.ViewStack(); self._vstack.set_vexpand(True)

        self._ss=Gio.ListStore.new(SongObject)
        self._sf=Gtk.FilterListModel.new(self._ss,Gtk.CustomFilter.new(self._sfunc,None))
        lv=self._make_song_lv(self._sf); self._slv=lv
        self._vstack.add_titled_with_icon(self._wrap(lv),"songs","Canciones","audio-x-generic-symbolic")

        self._as_al=Gio.ListStore.new(StrObj)
        self._vstack.add_titled_with_icon(self._wrap(self._make_lib_lv(self._as_al,self._on_album_act,"album")),"albums","Albums","media-optical-symbolic")

        self._as_ar=Gio.ListStore.new(StrObj)
        self._vstack.add_titled_with_icon(self._wrap(self._make_lib_lv(self._as_ar,self._on_artist_act,"artist")),"artists","Artistas","system-users-symbolic")

        self._as_ge=Gio.ListStore.new(StrObj)
        self._vstack.add_titled_with_icon(self._wrap(self._make_lib_lv(self._as_ge,self._on_genre_act,"genre")),"genres","Generos","applications-multimedia-symbolic")

        bar=Adw.ViewSwitcherBar(); bar.set_stack(self._vstack); bar.set_reveal(True)
        box.append(self._vstack); box.append(bar); return box

    def _wrap(self,w):
        sw=Gtk.ScrolledWindow(); sw.set_policy(Gtk.PolicyType.NEVER,Gtk.PolicyType.AUTOMATIC)
        sw.set_vexpand(True); sw.set_child(w); return sw

    def _make_song_lv(self,model):
        lv=Gtk.ListView(); lv.add_css_class("navigation-sidebar")
        f=Gtk.SignalListItemFactory()
        f.connect("setup",self._setup_song_row); f.connect("bind",self._bind_song_row)
        lv.set_model(Gtk.SingleSelection.new(model)); lv.set_factory(f)
        lv.connect("activate",self._on_song_act); return lv

    def _setup_song_row(self,_,item):
        row=Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,spacing=8)
        row.set_margin_start(8); row.set_margin_end(8); row.set_margin_top(4); row.set_margin_bottom(4)
        num=Gtk.Label(); num.set_width_chars(3); num.add_css_class("dim-label"); num.add_css_class("row-sub"); num.set_xalign(1)
        tb=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=1); tb.set_hexpand(True)
        tl=Gtk.Label(); tl.add_css_class("row-title"); tl.set_halign(Gtk.Align.START); tl.set_ellipsize(Pango.EllipsizeMode.END)
        sl=Gtk.Label(); sl.add_css_class("row-sub"); sl.add_css_class("dim-label"); sl.set_halign(Gtk.Align.START); sl.set_ellipsize(Pango.EllipsizeMode.END)
        tb.append(tl); tb.append(sl)
        dl=Gtk.Label(); dl.add_css_class("row-sub"); dl.add_css_class("dim-label")
        row.append(num); row.append(tb); row.append(dl); item.set_child(row)

    def _bind_song_row(self,_,item):
        obj=item.get_item(); s=obj.song; row=item.get_child()
        ws=[]; c=row.get_first_child()
        while c: ws.append(c); c=c.get_next_sibling()
        num,tb,dl=ws; tl=tb.get_first_child(); sl=tl.get_next_sibling()
        num.set_label(str(obj.position+1)); tl.set_label(s.display_title)
        sl.set_label(f"{s.artist} · {s.album}" if s.album else s.artist)
        dl.set_label(s.duration_str)
        if self.mqm.index==obj.position: row.add_css_class("active-row")
        else: row.remove_css_class("active-row")

    def _make_lib_lv(self,store,on_act,mode):
        lv=Gtk.ListView(); lv.add_css_class("navigation-sidebar")
        f=Gtk.SignalListItemFactory()
        f.connect("setup",lambda _,i: self._setup_lib_row(_,i,mode))
        f.connect("bind", lambda _,i: self._bind_lib_row(_,i,mode))
        lv.set_model(Gtk.SingleSelection.new(store)); lv.set_factory(f)
        lv.connect("activate",on_act); return lv

    def _setup_lib_row(self,_,item,mode):
        row=Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,spacing=12)
        row.set_margin_start(12); row.set_margin_end(12); row.set_margin_top(6); row.set_margin_bottom(6)
        icons={"album":"media-optical-symbolic","artist":"avatar-default-symbolic","genre":"applications-multimedia-symbolic"}
        ico=Gtk.Image.new_from_icon_name(icons[mode]); ico.set_pixel_size(32); ico.set_opacity(0.5)
        tb=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=2); tb.set_hexpand(True)
        tl=Gtk.Label(); tl.add_css_class("lib-title"); tl.set_halign(Gtk.Align.START); tl.set_ellipsize(Pango.EllipsizeMode.END)
        sl=Gtk.Label(); sl.add_css_class("lib-sub"); sl.add_css_class("dim-label"); sl.set_halign(Gtk.Align.START)
        tb.append(tl); tb.append(sl)
        arr=Gtk.Image.new_from_icon_name("go-next-symbolic"); arr.set_opacity(0.3)
        row.append(ico); row.append(tb); row.append(arr); item.set_child(row)

    def _bind_lib_row(self,_,item,mode):
        obj=item.get_item(); row=item.get_child()
        ws=[]; c=row.get_first_child()
        while c: ws.append(c); c=c.get_next_sibling()
        _,tb,_=ws; tl=tb.get_first_child(); sl=tl.get_next_sibling()
        tl.set_label(obj.text)
        if obj.data is not None:
            if mode=="album":  artist,count=obj.data; sl.set_label(f"{artist}  ·  {count} canciones")
            elif mode=="artist": sl.set_label(f"{obj.data} canciones")
            elif mode=="genre":  sl.set_label(f"{obj.data} canciones")

    def _build_menu(self):
        m=Gio.Menu()
        m.append("Abrir carpeta","app.open_folder")
        m.append("Reescanear biblioteca","app.rescan")
        m.append("Acerca de","app.about"); return m

    # ── Search ──────────────────────────────
    def _sfunc(self,item,_):
        q=self._sentry.get_text().strip().lower()
        if not q: return True
        s=item.song; return q in s.title.lower() or q in s.artist.lower() or q in s.album.lower()
    def _on_search_toggled(self,btn):
        if not btn.get_active(): self._sentry.set_text(""); self._rfilter()
    def _on_search_changed(self,_): self._rfilter()
    def _rfilter(self):
        f=self._sf.get_filter()
        if f: f.changed(Gtk.FilterChange.DIFFERENT)

    # ── Folder ──────────────────────────────
    def _on_open(self,_=None):
        d=Gtk.FileDialog(); d.set_title("Seleccionar carpeta de musica")
        d.select_folder(self,None,self._folder_cb)
    def _folder_cb(self,dialog,result):
        try:
            f=dialog.select_folder_finish(result)
            if f: self._load_folder(f.get_path())
        except GLib.Error: pass

    def _load_folder(self,folder):
        self._folder=folder
        if self.db.is_indexed(folder) and not self.db.needs_rescan(folder):
            self.db.remove_missing(folder)
            songs=self.db.songs_in_folder(folder)
            self._populate(songs); self._lstat.set_label(f"{len(songs)} canciones"); return
        self._scan(folder)

    def _scan(self,folder):
        self._spin.set_visible(True); self._spin.start(); self._lstat.set_label("Escaneando...")
        def work():
            songs=[]
            for root,_,files in os.walk(folder):
                for f in sorted(files):
                    if Path(f).suffix.lower() in SUPPORTED_FORMATS:
                        s=Song.from_path(os.path.join(root,f))
                        self.db.upsert(s,folder); songs.append(s)
            self.db.commit(); self.db.remove_missing(folder)
            GLib.idle_add(self._scan_done,songs)
        threading.Thread(target=work,daemon=True).start()

    def _scan_done(self,songs):
        self._spin.stop(); self._spin.set_visible(False)
        self._populate(songs); self._lstat.set_label(f"{len(songs)} canciones")

    def _populate(self,songs):
        self._ss.remove_all()
        for i,s in enumerate(songs): self._ss.append(SongObject(s,i))
        self.mqm.set_songs(songs,0)
        self._as_al.remove_all()
        for album,artist,count in self.db.all_albums():
            self._as_al.append(StrObj(album,(artist,count)))
        self._as_ar.remove_all()
        for artist,count in self.db.all_artists(): self._as_ar.append(StrObj(artist,count))
        self._as_ge.remove_all()
        for genre,count in self.db.all_genres(): self._as_ge.append(StrObj(genre,count))
        self._wtitle.set_subtitle(f"{len(songs)} canciones en biblioteca")

    # ── Library activations ──────────────────
    def _on_album_act(self,_,pos):
        obj=self._as_al.get_item(pos)
        if obj: self._subview(f"Album: {obj.text}",self.db.songs_by_album(obj.text,obj.data[0]))
    def _on_artist_act(self,_,pos):
        obj=self._as_ar.get_item(pos)
        if obj: self._subview(f"Artista: {obj.text}",self.db.songs_by_artist(obj.text))
    def _on_genre_act(self,_,pos):
        obj=self._as_ge.get_item(pos)
        if obj: self._subview(f"Genero: {obj.text}",self.db.songs_by_genre(obj.text))

    def _subview(self,title,songs):
        dlg=Adw.Dialog(); dlg.set_title(title); dlg.set_content_width(560); dlg.set_content_height(520)
        box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        hdr=Adw.HeaderBar()
        hdr.set_title_widget(Adw.WindowTitle(title=title,subtitle=f"{len(songs)} canciones"))
        box.append(hdr)
        pa=Gtk.Button(label="Reproducir todo"); pa.add_css_class("suggested-action")
        pa.set_margin_start(12); pa.set_margin_end(12); pa.set_margin_top(8); pa.set_margin_bottom(4)
        pa.connect("clicked",lambda _: self._play_list(songs,0,dlg)); box.append(pa)
        store=Gio.ListStore.new(SongObject)
        for i,s in enumerate(songs): store.append(SongObject(s,i))
        sw=Gtk.ScrolledWindow(); sw.set_policy(Gtk.PolicyType.NEVER,Gtk.PolicyType.AUTOMATIC); sw.set_vexpand(True)
        lv=Gtk.ListView(); lv.add_css_class("navigation-sidebar")
        f=Gtk.SignalListItemFactory(); f.connect("setup",self._setup_song_row)
        def bind_sub(_,item):
            obj2=item.get_item(); s2=obj2.song; row=item.get_child()
            ws=[]; c=row.get_first_child()
            while c: ws.append(c); c=c.get_next_sibling()
            num,tb,dl=ws; tl=tb.get_first_child(); sl=tl.get_next_sibling()
            num.set_label(str(obj2.position+1)); tl.set_label(s2.display_title)
            sl.set_label(f"{s2.artist} · {s2.album}" if s2.album else s2.artist)
            dl.set_label(s2.duration_str)
        f.connect("bind",bind_sub)
        lv.set_model(Gtk.SingleSelection.new(store)); lv.set_factory(f)
        lv.connect("activate",lambda lv2,p: self._play_list(songs,p,dlg))
        sw.set_child(lv); box.append(sw); dlg.set_child(box); dlg.present(self)

    def _play_list(self,songs,start,dlg=None):
        if dlg: dlg.close()
        self.mqm.set_songs(songs,start)
        self._ss.remove_all()
        for i,s in enumerate(songs): self._ss.append(SongObject(s,i))
        self._vstack.set_visible_child_name("songs"); self._play_current()

    # ── Multi-queue ──────────────────────────
    def _on_queue_btn(self,btn,idx):
        if btn.get_active():
            for i,b in enumerate(self._qbtns):
                if i!=idx: b.set_active(False)
            self.mqm.switch(idx)
            # Refrescar lista con canciones de la nueva cola
            songs=self.mqm.songs
            self._ss.remove_all()
            for i,s in enumerate(songs): self._ss.append(SongObject(s,i))
            n=self.mqm.queue.count
            self._lstat.set_label(f"Cola Q{idx+1}: {n} canciones")

    def _on_add_to_queue(self,_):
        s=self.mqm.current
        if not s: return
        # Agregar cancion actual a la siguiente cola
        nxt=(self.mqm.active_idx+1)%MultiQueueManager.NUM_QUEUES
        self.mqm.add_to_queue(nxt,s)
        toast=Adw.Toast.new(f"Agregado a Q{nxt+1}")
        toast.set_timeout(2)
        # Mostrar toast si hay ToastOverlay (simplificado)
        self._lstat.set_label(f"Agregado a Q{nxt+1}")

    # ── Tag editor ──────────────────────────
    def _on_edit_tags(self,_):
        s=self.mqm.current
        if not s: return
        TagEditorDialog(s,self._on_tags_saved,self)

    def _on_tags_saved(self,song):
        self.db.update_tags(song.path,song.title,song.artist,song.album,song.genre,song.tracknumber)
        self._update_player(song)
        n=self._ss.get_n_items()
        if n: self._ss.items_changed(0,n,n)

    # ── Playback ────────────────────────────
    def _on_song_act(self,_,pos):
        obj=self._sf.get_item(pos)
        if not obj: return
        self.mqm.index=obj.position; self._play_current()

    def _play_current(self):
        s=self.mqm.current
        if not s: return
        s.load_cover(); self.engine.load(s.path); self.engine.play()
        self._update_player(s)
        nxt=self.mqm.peek_next()
        # Crossfade handling
        if self.engine._xfade_secs>0 and nxt:
            dur=s.duration
            if dur>self.engine._xfade_secs:
                GLib.timeout_add(int((dur-self.engine._xfade_secs)*1000),
                    lambda: self.engine.load_next_for_xfade(nxt.path) or False)
        n=self._ss.get_n_items()
        if n: self._ss.items_changed(0,n,n)
        self.mpris.notify()

    def _update_player(self,s):
        self._bpl.set_icon_name("media-playback-pause-symbolic")
        self._lt.set_label(s.display_title)
        self._lar.set_label(s.artist or "Artista desconocido")
        self._lab.set_label(s.album or "")
        self._wtitle.set_subtitle(f"{s.title} — {s.artist}")
        self._seek.set_range(0,max(s.duration,1)); self._seek.set_value(0)
        self._ldur.set_label(s.duration_str); self._load_cover(s)

    def _load_cover(self,s):
        if s.cover:
            try:
                ld=GdkPixbuf.PixbufLoader(); ld.write(s.cover); ld.close()
                self._cimg.set_pixbuf(ld.get_pixbuf()); self._cstack.set_visible_child_name("cover"); return
            except: pass
        self._cstack.set_visible_child_name("ph")

    def _on_play_pause(self,_=None):
        if not self.mqm.current:
            if self.mqm.songs: self._play_current()
            return
        if self.engine.is_playing:
            self.engine.pause(); self._bpl.set_icon_name("media-playback-start-symbolic")
        else:
            self.engine.play(); self._bpl.set_icon_name("media-playback-pause-symbolic")
        self.mpris.notify()

    def _on_next(self,_=None):
        if self.mqm.next(): self._play_current()
        else: self.engine.stop(); self._bpl.set_icon_name("media-playback-start-symbolic")

    def _on_prev(self,_=None):
        if self.engine.position>3.0: self.engine.seek(0)
        else: self.mqm.prev(); self._play_current()

    def _on_eos(self): self._on_next()
    def _on_eng_err(self,msg): self._on_next()

    def _on_repeat(self,_):
        m=self.mqm.next_repeat()
        self._brp.set_icon_name("media-playlist-repeat-song-symbolic" if m==REPEAT_ONE else "media-playlist-repeat-symbolic")
        if m==REPEAT_ALL: self._brp.add_css_class("suggested-action")
        else: self._brp.remove_css_class("suggested-action")

    def _on_seek_change(self,_,__,v):
        if self._seeking: m,s=divmod(int(v),60); self._lpos.set_label(f"{m}:{s:02d}")
        return False
    def _on_seek_rel(self,*_): self.engine.seek(self._seek.get_value()); self._seeking=False
    def _on_vol(self,sc):
        v=sc.get_value(); self.engine.set_volume(v)
        self._vico.set_from_icon_name(
            "audio-volume-muted-symbolic" if v==0 else
            "audio-volume-low-symbolic" if v<.33 else
            "audio-volume-medium-symbolic" if v<.66 else
            "audio-volume-high-symbolic")

    def _update_pos(self,pos,dur):
        if self._seeking or dur==0: return
        self._seek.set_value(pos); m,s=divmod(int(pos),60); self._lpos.set_label(f"{m}:{s:02d}")
        # Precargar crossfade cuando queden X segundos
        if self.engine._xfade_secs>0 and dur>0:
            remaining=dur-pos
            if 0<remaining<=self.engine._xfade_secs and not self.engine._xfading:
                nxt=self.mqm.peek_next()
                if nxt: self.engine.load_next_for_xfade(nxt.path)
# ══ Application ════════════════════════════════════════════════════════
class ArgOSMusicApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="com.argos.musicplayer",flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.connect("activate",self._on_activate)
        for name,cb in [
            ("open_folder",lambda a,p: self.win._on_open()),
            ("rescan",     lambda a,p: self.win._scan(self.win._folder) if self.win._folder else None),
            ("about",      self._about),
        ]:
            act=Gio.SimpleAction.new(name,None); act.connect("activate",cb); self.add_action(act)

    def _on_activate(self,_):
        self.win=ArgOSMusicPlayer(self); self.win.present()

    def _about(self,*_):
        Adw.AboutDialog(
            application_name="ArgOS Music Player",application_icon="audio-x-generic",
            version="1.0.0",developer_name="Andres · ArgOS Platinum Edition",
            comments="Reproductor local con EQ, crossfade, colas multiples, MPRIS2 y editor de etiquetas.",
            license_type=Gtk.License.GPL_3_0).present(self.win)

def main():
    app=ArgOSMusicApp(); sys.exit(app.run(sys.argv))

if __name__=="__main__":
    main()

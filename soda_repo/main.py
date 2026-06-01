"""
汽水音乐风格播放器 — Kivy + ffpyplayer
核心体验：上下滑动切歌 · 唱片旋转动画 · 深色主题
"""

import os
import sys
import threading
import time
import math

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.carousel import Carousel
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.slider import Slider
from kivy.uix.image import Image
from kivy.uix.widget import Widget
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock
from kivy.animation import Animation
from kivy.graphics import Color, Ellipse, Rectangle, RoundedRectangle, Rotate, PushMatrix, PopMatrix
from kivy.graphics.texture import Texture
from kivy.core.window import Window
from kivy.core.audio import SoundLoader
from kivy.properties import (
    NumericProperty, StringProperty, BooleanProperty, ObjectProperty, ListProperty
)
from kivy.metrics import dp, sp
from kivy.utils import get_color_from_hex
from kivy.lang import Builder
from kivy.uix.filechooser import FileChooserIconView
from kivy.uix.popup import Popup

# ── 音频引擎 ──────────────────────────────────────────────
class AudioEngine:
    """基于 Kivy SoundLoader 的音频播放控制器"""
    def __init__(self):
        self._sound = None
        self._playlist = []
        self._index = -1
        self._volume = 0.7
        self._seek_pos = 0.0
        self._paused = False
        self._duration = 0.0
        self._state = "stopped"  # stopped/playing/paused

    @property
    def playlist(self):
        return self._playlist

    @property
    def current_index(self):
        return self._index

    @property
    def current_path(self):
        if 0 <= self._index < len(self._playlist):
            return self._playlist[self._index]
        return ""

    @property
    def current_name(self):
        path = self.current_path
        return os.path.basename(path) if path else ""

    @property
    def position(self):
        if self._sound and self._state != "stopped":
            return self._sound.get_pos()
        return 0.0

    @property
    def duration(self):
        if self._sound:
            return self._sound.length or self._duration
        return self._duration

    @property
    def volume(self):
        return self._volume

    @property
    def is_playing(self):
        return self._state == "playing"

    @property
    def is_paused(self):
        return self._state == "paused"

    @property
    def state(self):
        return self._state

    def add_files(self, paths):
        supported = (".mp3", ".wav", ".ogg", ".flac", ".m4a", ".aac", ".wma")
        for p in paths:
            ext = os.path.splitext(p)[1].lower()
            if ext in supported and p not in self._playlist:
                self._playlist.append(p)
        if self._index == -1 and self._playlist:
            self._index = 0

    def add_folder(self, folder_path):
        supported = (".mp3", ".wav", ".ogg", ".flac", ".m4a", ".aac", ".wma")
        files = []
        for root_dir, dirs, files_in_dir in os.walk(folder_path):
            for f in files_in_dir:
                if os.path.splitext(f)[1].lower() in supported:
                    files.append(os.path.join(root_dir, f))
        self.add_files(files)

    def remove_index(self, idx):
        if 0 <= idx < len(self._playlist):
            was_playing_current = (idx == self._index and self._state != "stopped")
            del self._playlist[idx]
            if not self._playlist:
                self._index = -1
                self.stop()
                return
            if idx < self._index:
                self._index -= 1
            elif idx == self._index:
                self.stop()
                self._index = min(self._index, len(self._playlist) - 1)

    def play(self, index=-1):
        if index >= 0:
            self._index = index
        if self._index < 0 or self._index >= len(self._playlist):
            return False
        path = self._playlist[self._index]
        try:
            if self._sound:
                self._sound.stop()
                self._sound.unload()
            self._sound = SoundLoader.load(path)
            if not self._sound:
                return False
            self._sound.volume = self._volume
            self._sound.play()
            self._sound.seek(self._seek_pos if self._seek_pos > 0 else 0)
            self._seek_pos = 0
            self._duration = self._sound.length or 0
            self._state = "playing"
            self._paused = False
            return True
        except Exception as e:
            print(f"Play error: {e}")
            return False

    def toggle_play_pause(self):
        if self._state == "playing":
            if self._sound:
                self._sound.stop()
            self._state = "paused"
            self._paused = True
            self._seek_pos = self.position
        elif self._state == "paused":
            self.play()
        else:
            self.play()

    def stop(self):
        if self._sound:
            self._sound.stop()
            self._sound.unload()
            self._sound = None
        self._state = "stopped"
        self._paused = False
        self._seek_pos = 0

    def next(self):
        if self._playlist:
            self._index = (self._index + 1) % len(self._playlist)
            self.play()

    def prev(self):
        if self._playlist:
            self._index = (self._index - 1) % len(self._playlist)
            self.play()

    def set_volume(self, v):
        self._volume = max(0.0, min(1.0, v))
        if self._sound:
            self._sound.volume = self._volume

    def seek(self, pos_sec):
        if self._sound:
            self._sound.seek(pos_sec)
            self._seek_pos = pos_sec

    def cleanup(self):
        self.stop()


# ── 唱片 Widget ───────────────────────────────────────────
class VinylDisc(Widget):
    """带旋转动画的圆形唱片"""
    angle = NumericProperty(0)
    is_rotating = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._rotation_speed = 72  # 度/秒
        self._rot_anim = None
        self.bind(size=self._update_canvas, pos=self._update_canvas)
        Clock.schedule_interval(self._rotate_tick, 1/30)

    def _update_canvas(self, *args):
        self.canvas.clear()
        cx, cy = self.center_x, self.center_y
        r = min(self.width, self.height) / 2 - dp(4)

        with self.canvas:
            # 旋转
            PushMatrix()
            Rotate(origin=(cx, cy), angle=self.angle)

            # 唱片底（深色大圆）
            Color(*get_color_from_hex("#1a1a2e"))
            Ellipse(pos=(cx - r, cy - r), size=(r * 2, r * 2))

            # 唱片沟槽圈
            for groove_r in [r * 0.85, r * 0.70, r * 0.55, r * 0.40]:
                Color(*get_color_from_hex("#252540"), 1)
                from kivy.graphics import Line
                # 用多个同心圆模拟沟槽
                Color(*get_color_from_hex("#2a2a45"), 0.6)
                Ellipse(
                    pos=(cx - groove_r, cy - groove_r),
                    size=(groove_r * 2, groove_r * 2)
                )

            # 中心标签（彩色圆）
            Color(*get_color_from_hex("#ff6b9d"))
            label_r = r * 0.22
            Ellipse(
                pos=(cx - label_r, cy - label_r),
                size=(label_r * 2, label_r * 2)
            )

            # 中心小孔
            Color(*get_color_from_hex("#121218"))
            hole_r = r * 0.06
            Ellipse(
                pos=(cx - hole_r, cy - hole_r),
                size=(hole_r * 2, hole_r * 2)
            )

            PopMatrix()

    def _rotate_tick(self, dt):
        if self.is_rotating:
            self.angle = (self.angle + self._rotation_speed * dt) % 360

    def start_rotation(self):
        self.is_rotating = True

    def stop_rotation(self):
        self.is_rotating = False


# ── 歌曲卡片（单页） ─────────────────────────────────────
class SongCard(FloatLayout):
    """汽水音乐风格的单首歌曲卡片"""
    song_path = StringProperty("")
    song_name = StringProperty("未知歌曲")
    song_artist = StringProperty("未知艺术家")

    def __init__(self, path="", **kwargs):
        super().__init__(**kwargs)
        self.song_path = path
        if path:
            self.song_name = os.path.splitext(os.path.basename(path))[0]
        self._build()

    def _build(self):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*get_color_from_hex("#0d0d1a"))
            Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_bg, size=self._update_bg)

        # 唱片
        self.vinyl = VinylDisc(
            size_hint=(None, None),
            size=(dp(240), dp(240)),
            pos_hint={"center_x": 0.5, "center_y": 0.58}
        )
        self.add_widget(self.vinyl)

        # 歌曲名
        self.lbl_name = Label(
            text=self.song_name,
            font_name="",
            font_size=sp(20),
            bold=True,
            color=get_color_from_hex("#ffffff"),
            size_hint=(1, None),
            height=dp(36),
            pos_hint={"center_x": 0.5, "top": 0.56},
            halign="center",
            valign="middle"
        )
        # 文字截断
        self.lbl_name.bind(size=self.lbl_name.setter('text_size'))
        self.add_widget(self.lbl_name)

        # 艺术家（从文件名或路径提取）
        artist = self._guess_artist()
        self.lbl_artist = Label(
            text=artist,
            font_size=sp(14),
            color=get_color_from_hex("#888899"),
            size_hint=(1, None),
            height=dp(24),
            pos_hint={"center_x": 0.5, "top": 0.665},
            halign="center",
            valign="middle"
        )
        self.lbl_artist.bind(size=self.lbl_artist.setter('text_size'))
        self.add_widget(self.lbl_artist)

    def _update_bg(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*get_color_from_hex("#0d0d1a"))
            Rectangle(pos=self.pos, size=self.size)

    def _guess_artist(self):
        path = self.song_path
        # 尝试从路径中提取艺术家（文件夹名）
        parts = path.replace("\\", "/").split("/")
        if len(parts) >= 2:
            return parts[-2]
        return "未知艺术家"

    def update_info(self, name, artist=""):
        self.song_name = name
        self.lbl_name.text = name
        if artist:
            self.song_artist = artist
            self.lbl_artist.text = artist


# ── 主界面 ────────────────────────────────────────────────
class SodaMusicPlayer(FloatLayout):
    """汽水音乐风格主界面"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.engine = AudioEngine()
        self._touching_slider = False
        self._build_ui()

        # 进度更新时钟
        Clock.schedule_interval(self._update_progress, 1/10)

    def _build_ui(self):
        # 背景
        with self.canvas.before:
            Color(*get_color_from_hex("#0d0d1a"))
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(size=self._update_bg, pos=self._update_bg)

        # 垂直滑动切歌
        self.carousel = Carousel(
            direction="top",
            loop=True,
            anim_move_duration=0.35,
            size_hint=(1, 1)
        )
        self.add_widget(self.carousel)

        # 底部控制栏（半透明毛玻璃效果）
        self.control_bar = FloatLayout(
            size_hint=(1, None),
            height=dp(160),
            pos_hint={"x": 0, "y": 0}
        )
        with self.control_bar.canvas.before:
            Color(0.06, 0.06, 0.12, 0.92)
            self.ctrl_bg = RoundedRectangle(
                pos=self.control_bar.pos,
                size=self.control_bar.size,
                radius=[dp(20), dp(20), 0, 0]
            )
        self.control_bar.bind(pos=self._update_ctrl_bg, size=self._update_ctrl_bg)
        self.add_widget(self.control_bar)

        # 进度条
        self.progress_slider = Slider(
            min=0, max=100, value=0,
            size_hint=(0.9, None),
            height=dp(24),
            pos_hint={"center_x": 0.5, "top": 1.0},
            cursor_size=(dp(14), dp(14)),
            background_width=dp(3),
            value_track=True,
            value_track_color=get_color_from_hex("#ff6b9d"),
            background_disabled_color=get_color_from_hex("#333355")
        )
        self.progress_slider.bind(
            on_touch_down=self._on_slider_touch_down,
            on_touch_up=self._on_slider_touch_up,
            value=self._on_slider_value
        )
        self.control_bar.add_widget(self.progress_slider)

        # 时间标签
        self.lbl_time = Label(
            text="00:00 / 00:00",
            font_size=sp(11),
            color=get_color_from_hex("#666688"),
            size_hint=(0.9, None),
            height=dp(18),
            pos_hint={"center_x": 0.5, "y": 0.77},
            halign="center"
        )
        self.lbl_time.bind(size=self.lbl_time.setter('text_size'))
        self.control_bar.add_widget(self.lbl_time)

        # 歌曲名（控制栏内）
        self.lbl_title_bar = Label(
            text="未在播放",
            font_size=sp(15),
            bold=True,
            color=get_color_from_hex("#ffffff"),
            size_hint=(0.86, None),
            height=dp(24),
            pos_hint={"center_x": 0.5, "y": 0.60},
            halign="center"
        )
        self.lbl_title_bar.bind(size=self.lbl_title_bar.setter('text_size'))
        self.control_bar.add_widget(self.lbl_title_bar)

        # 按钮行
        btn_y = 0.08
        btn_size = (dp(44), dp(44))

        # 上一首
        self.btn_prev = Button(
            text="⏮",
            font_size=sp(22),
            size_hint=(None, None),
            size=btn_size,
            pos_hint={"center_x": 0.22, "y": btn_y},
            background_color=(1, 1, 1, 0),
            color=get_color_from_hex("#cccdde")
        )
        self.btn_prev.bind(on_press=lambda x: self._prev_song())
        self.control_bar.add_widget(self.btn_prev)

        # 播放/暂停（大按钮）
        self.btn_play = Button(
            text="▶",
            font_size=sp(28),
            size_hint=(None, None),
            size=(dp(60), dp(60)),
            pos_hint={"center_x": 0.5, "y": 0.06},
            background_color=get_color_from_hex("#ff6b9d"),
            background_normal="",
            color=get_color_from_hex("#ffffff")
        )
        self.btn_play.bind(on_press=lambda x: self._toggle_play())
        self.control_bar.add_widget(self.btn_play)

        # 下一首
        self.btn_next = Button(
            text="⏭",
            font_size=sp(22),
            size_hint=(None, None),
            size=btn_size,
            pos_hint={"center_x": 0.78, "y": btn_y},
            background_color=(1, 1, 1, 0),
            color=get_color_from_hex("#cccdde")
        )
        self.btn_next.bind(on_press=lambda x: self._next_song())
        self.control_bar.add_widget(self.btn_next)

        # 音量按钮
        self.btn_vol = Button(
            text="🔊",
            font_size=sp(16),
            size_hint=(None, None),
            size=(dp(32), dp(32)),
            pos_hint={"x": 0.87, "y": btn_y + 0.02},
            background_color=(1, 1, 1, 0),
            color=get_color_from_hex("#8888aa")
        )
        self.btn_vol.bind(on_press=lambda x: self._toggle_mute())
        self.control_bar.add_widget(self.btn_vol)

        # 添加歌曲按钮
        self.btn_add = Button(
            text="＋",
            font_size=sp(22),
            size_hint=(None, None),
            size=(dp(32), dp(32)),
            pos_hint={"x": 0.05, "y": btn_y + 0.02},
            background_color=(1, 1, 1, 0),
            color=get_color_from_hex("#8888aa")
        )
        self.btn_add.bind(on_press=lambda x: self._show_add_menu())
        self.control_bar.add_widget(self.btn_add)

    # ── UI 回调 ──
    def _update_bg(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size

    def _update_ctrl_bg(self, *args):
        self.ctrl_bg.pos = self.control_bar.pos
        self.ctrl_bg.size = self.control_bar.size

    def _on_slider_touch_down(self, instance, touch):
        if instance.collide_point(*touch.pos):
            self._touching_slider = True

    def _on_slider_touch_up(self, instance, touch):
        if self._touching_slider:
            self._touching_slider = False
            dur = self.engine.duration
            if dur > 0:
                pos = self.progress_slider.value / 100 * dur
                self.engine.seek(pos)

    def _on_slider_value(self, instance, value):
        if self._touching_slider:
            dur = self.engine.duration
            if dur > 0:
                pos = value / 100 * dur
                m, s = divmod(int(pos), 60)
                dm, ds = divmod(int(dur), 60)
                self.lbl_time.text = f"{m:02d}:{s:02d} / {dm:02d}:{ds:02d}"

    def _update_progress(self, dt):
        if self.engine.is_playing and not self._touching_slider:
            pos = self.engine.position
            dur = self.engine.duration
            if dur > 0:
                pct = pos / dur * 100
                self.progress_slider.value = min(pct, 100)
                m, s = divmod(int(pos), 60)
                dm, ds = divmod(int(dur), 60)
                self.lbl_time.text = f"{m:02d}:{s:02d} / {dm:02d}:{ds:02d}"
                # 自动切歌
                if pos >= dur - 0.5:
                    self._on_song_end()

    def _on_song_end(self):
        Clock.schedule_once(lambda dt: self._next_song(), 0.1)

    # ── 播放控制 ──
    def _toggle_play(self):
        if not self.engine.playlist:
            self._show_add_menu()
            return
        self.engine.toggle_play_pause()
        self._sync_ui_state()

    def _next_song(self):
        if not self.engine.playlist:
            return
        self.engine.next()
        self._switch_to_current()
        self._sync_ui_state()

    def _prev_song(self):
        if not self.engine.playlist:
            return
        self.engine.prev()
        self._switch_to_current()
        self._sync_ui_state()

    def _switch_to_current(self):
        idx = self.engine.current_index
        if 0 <= idx < len(self.carousel.slides):
            self.carousel.load_slide(self.carousel.slides[idx])
        self._update_vinyl_states()

    def _update_vinyl_states(self):
        """更新所有卡片的唱片旋转状态"""
        current_idx = self.engine.current_index
        for i, slide in enumerate(self.carousel.slides):
            if hasattr(slide, 'vinyl'):
                if i == current_idx and self.engine.is_playing:
                    slide.vinyl.start_rotation()
                else:
                    slide.vinyl.stop_rotation()

    def _toggle_mute(self):
        if self.engine.volume > 0.01:
            self._last_volume = self.engine.volume
            self.engine.set_volume(0)
            self.btn_vol.text = "🔇"
        else:
            self.engine.set_volume(getattr(self, '_last_volume', 0.7))
            self.btn_vol.text = "🔊"

    def _sync_ui_state(self):
        is_playing = self.engine.is_playing
        self.btn_play.text = "⏸" if is_playing else "▶"
        # 更新当前卡片信息
        cur = self.engine.current_name
        if cur:
            name = os.path.splitext(cur)[0]
            self.lbl_title_bar.text = name
        # 唱片状态
        self._update_vinyl_states()

    # ── 歌曲管理 ──
    def _show_add_menu(self):
        """弹出添加歌曲菜单"""
        content = BoxLayout(orientation="vertical", spacing=dp(10), padding=dp(20))

        btn_files = Button(
            text="从文件选择",
            size_hint=(1, None),
            height=dp(48),
            background_color=get_color_from_hex("#ff6b9d"),
            background_normal="",
            color=(1, 1, 1, 1)
        )
        btn_folder = Button(
            text="导入整个文件夹",
            size_hint=(1, None),
            height=dp(48),
            background_color=get_color_from_hex("#6b9dff"),
            background_normal="",
            color=(1, 1, 1, 1)
        )

        content.add_widget(Label(
            text="添加音乐",
            font_size=sp(18),
            color=get_color_from_hex("#ffffff"),
            size_hint=(1, None),
            height=dp(36)
        ))
        content.add_widget(btn_files)
        content.add_widget(btn_folder)

        popup = Popup(
            title="",
            content=content,
            size_hint=(0.75, 0.35),
            background_color=get_color_from_hex("#1a1a2e"),
            separator_color=(0, 0, 0, 0),
            title_color=(0, 0, 0, 0)
        )

        def add_files_callback(instance):
            popup.dismiss()
            Clock.schedule_once(lambda dt: self._open_file_chooser(), 0.3)

        def add_folder_callback(instance):
            popup.dismiss()
            Clock.schedule_once(lambda dt: self._open_folder_chooser(), 0.3)

        btn_files.bind(on_press=add_files_callback)
        btn_folder.bind(on_press=add_folder_callback)
        popup.open()

    def _open_file_chooser(self):
        """打开文件选择器"""
        content = BoxLayout(orientation="vertical")
        chooser = FileChooserIconView(
            filters=["*.mp3", "*.wav", "*.ogg", "*.flac", "*.m4a", "*.aac", "*.wma"],
            path=os.path.expanduser("~\\Music") if os.path.exists(
                os.path.expanduser("~\\Music")) else os.path.expanduser("~"),
            multiselect=True
        )
        content.add_widget(chooser)

        btn_bar = BoxLayout(size_hint=(1, None), height=dp(48), spacing=dp(10))
        btn_cancel = Button(text="取消", background_color=get_color_from_hex("#333355"),
                            background_normal="")
        btn_ok = Button(text="添加选中", background_color=get_color_from_hex("#ff6b9d"),
                        background_normal="")

        popup = Popup(
            title="选择音乐文件",
            content=content,
            size_hint=(0.9, 0.75),
            background_color=get_color_from_hex("#1a1a2e")
        )

        def on_ok(instance):
            popup.dismiss()
            selected = chooser.selection
            if selected:
                self._add_and_play(selected)

        def on_cancel(instance):
            popup.dismiss()

        btn_ok.bind(on_press=on_ok)
        btn_cancel.bind(on_press=on_cancel)
        btn_bar.add_widget(btn_cancel)
        btn_bar.add_widget(btn_ok)
        content.add_widget(btn_bar)

        popup.open()

    def _open_folder_chooser(self):
        content = BoxLayout(orientation="vertical")
        chooser = FileChooserIconView(
            dirselect=True,
            path=os.path.expanduser("~\\Music") if os.path.exists(
                os.path.expanduser("~\\Music")) else os.path.expanduser("~"),
            multiselect=False
        )
        content.add_widget(chooser)

        btn_bar = BoxLayout(size_hint=(1, None), height=dp(48), spacing=dp(10))
        btn_cancel = Button(text="取消", background_color=get_color_from_hex("#333355"),
                            background_normal="")
        btn_ok = Button(text="导入此文件夹", background_color=get_color_from_hex("#6b9dff"),
                        background_normal="")

        popup = Popup(
            title="选择文件夹",
            content=content,
            size_hint=(0.9, 0.75),
            background_color=get_color_from_hex("#1a1a2e")
        )

        def on_ok(instance):
            popup.dismiss()
            folder = chooser.path
            if folder:
                self.engine.add_folder(folder)
                self._rebuild_carousel()
                if self.engine.playlist:
                    self.engine.play(0)
                    self._sync_ui_state()

        def on_cancel(instance):
            popup.dismiss()

        btn_ok.bind(on_press=on_ok)
        btn_cancel.bind(on_press=on_cancel)
        btn_bar.add_widget(btn_cancel)
        btn_bar.add_widget(btn_ok)
        content.add_widget(btn_bar)

        popup.open()

    def _add_and_play(self, paths):
        was_empty = not self.engine.playlist
        self.engine.add_files(paths)
        self._rebuild_carousel()
        if was_empty and self.engine.playlist:
            self.engine.play(0)
        elif not self.engine.is_playing and not self.engine.is_paused:
            self.engine.play(0)
        self._sync_ui_state()

    def _rebuild_carousel(self):
        self.carousel.clear_widgets()
        for path in self.engine.playlist:
            card = SongCard(path=path)
            self.carousel.add_widget(card)
        if self.engine.current_index >= 0:
            self.carousel.load_slide(self.carousel.slides[self.engine.current_index])
        self._sync_ui_state()

    def on_touch_down(self, touch):
        # 让 carousel 优先处理滑动
        return super().on_touch_down(touch)


# ── App 入口 ──────────────────────────────────────────────
class SodaMusicApp(App):
    def build(self):
        Window.size = (420, 740)
        Window.minimum_width = 360
        Window.minimum_height = 600
        self.title = "Soda 音乐"
        # 设置窗口图标颜色
        Window.clearcolor = get_color_from_hex("#0d0d1a")
        return SodaMusicPlayer()

    def on_stop(self):
        if hasattr(self.root, 'engine'):
            self.root.engine.cleanup()


if __name__ == "__main__":
    SodaMusicApp().run()
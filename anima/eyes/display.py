# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
Display window for the eyes using pygame.
"""

import os

import pygame  # type: ignore[import-not-found]
import threading
import queue
import ctypes
from typing import Callable
from loguru import logger
from .config import Config
from .face import Face
from .renderer import EyeRenderer


class EyesDisplay:
    """Manages the pygame window and rendering loop."""

    def __init__(self, config: Config | None = None):
        if config is None:
            config = Config()
        self._config = config
        self._face: Face | None = None
        self._renderer: EyeRenderer | None = None
        self._screen: pygame.Surface | None = None
        self._clock: pygame.time.Clock | None = None
        self._running = False
        self._command_queue: queue.Queue = queue.Queue()
        self._thread: threading.Thread | None = None
        self._borderless = False  # Current borderless state (can be toggled)
        self._last_click_time = 0  # For double-click detection

    @property
    def face(self) -> Face | None:
        return self._face

    def _create_window(self) -> pygame.Surface:
        """Create or recreate the window with current settings."""
        cfg = self._config.display
        flags = 0
        if cfg.fullscreen:
            flags |= pygame.FULLSCREEN
        if self._borderless:
            flags |= pygame.NOFRAME

        screen = pygame.display.set_mode((cfg.width * cfg.scale, cfg.height * cfg.scale), flags)
        pygame.display.set_caption(cfg.title)
        return screen

    def _toggle_borderless(self):
        """Toggle between borderless and normal window mode."""
        self._borderless = not self._borderless
        self._screen = self._create_window()
        # Re-apply always on top after window recreation
        pygame.time.wait(50)
        self._set_always_on_top()

    def _set_always_on_top(self):
        """Set the window to always be on top (Windows-specific)."""
        if os.name != "nt":
            return
        try:
            user32 = ctypes.windll.user32

            # Get handle by window title
            title = self._config.display.title
            hwnd = user32.FindWindowW(None, title)

            if not hwnd:
                # Fallback to pygame's handle
                wm_info = pygame.display.get_wm_info()
                hwnd = wm_info.get("window", 0)

            if not hwnd:
                logger.warning(f"Could not find window handle for '{title}'")
                return

            # Windows API constants
            HWND_TOPMOST = ctypes.c_void_p(-1)
            SWP_NOMOVE = 0x0002
            SWP_NOSIZE = 0x0001

            # Set window to topmost
            result = user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)

            if not result:
                error = ctypes.get_last_error()
                logger.warning(f"SetWindowPos failed, error={error}")
            else:
                logger.debug(f"SetWindowPos succeeded for hwnd={hwnd}")

        except Exception as e:
            logger.error(f"always_on_top exception: {e}")

    def _init_pygame(self):
        """Initialize pygame and create window."""
        cfg = self._config.display

        # Set window position before pygame.init() if specified
        if cfg.window_x is not None and cfg.window_y is not None:
            os.environ["SDL_VIDEO_WINDOW_POS"] = f"{cfg.window_x},{cfg.window_y}"

        pygame.init()

        self._borderless = cfg.borderless
        self._screen = self._create_window()

        # Small delay to let window fully initialize, then set always on top
        pygame.time.wait(100)
        self._set_always_on_top()

        self._clock = pygame.time.Clock()

        # Create renderer
        self._renderer = EyeRenderer(self._screen, cfg.scale, self._config.colors.eye_color, self._config.colors.background_color, cfg.smooth_corners)

        # Create face
        self._face = Face(self._config)
        self._face.set_emotion("normal")

    def _process_commands(self):
        """Process any pending commands from the queue."""
        while not self._command_queue.empty():
            try:
                cmd, args, kwargs = self._command_queue.get_nowait()
                cmd(*args, **kwargs)
            except queue.Empty:
                break

    def _main_loop(self):
        """Main rendering loop."""
        self._init_pygame()
        self._running = True
        frame_count = 0

        # Type assertions - these are guaranteed non-None after _init_pygame()
        assert self._renderer is not None
        assert self._face is not None
        assert self._clock is not None

        while self._running:
            # Handle pygame events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self._running = False
                elif event.type == pygame.KEYDOWN:
                    self._handle_key(event.key)
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:  # Left click
                        current_time = pygame.time.get_ticks()
                        if current_time - self._last_click_time < 400:  # Double-click threshold (ms)
                            self._toggle_borderless()
                        self._last_click_time = current_time

            # Process commands from MCP
            self._process_commands()

            # Re-assert always-on-top every second (60 frames)
            frame_count += 1
            if frame_count >= 60:
                frame_count = 0
                self._set_always_on_top()

            # Clear and draw
            self._renderer.clear()
            self._face.update()
            self._face.draw(self._renderer)

            # Present
            pygame.display.flip()
            self._clock.tick(self._config.display.fps)

        pygame.quit()

    def _handle_key(self, key: int):
        """Handle keyboard input."""
        if self._face is None:
            return

        from .presets import Emotion

        key_emotions = {
            pygame.K_1: Emotion.NORMAL,
            pygame.K_2: Emotion.ANGRY,
            pygame.K_3: Emotion.GLEE,
            pygame.K_4: Emotion.HAPPY,
            pygame.K_5: Emotion.SAD,
            pygame.K_6: Emotion.WORRIED,
            pygame.K_7: Emotion.FOCUSED,
            pygame.K_8: Emotion.ANNOYED,
            pygame.K_9: Emotion.SURPRISED,
            pygame.K_0: Emotion.SKEPTIC,
            pygame.K_F1: Emotion.FRUSTRATED,
            pygame.K_F2: Emotion.UNIMPRESSED,
            pygame.K_F3: Emotion.SLEEPY,
            pygame.K_F4: Emotion.SUSPICIOUS,
            pygame.K_F5: Emotion.SQUINT,
            pygame.K_F6: Emotion.FURIOUS,
            pygame.K_F7: Emotion.SCARED,
            pygame.K_F8: Emotion.AWE,
        }

        if key == pygame.K_ESCAPE:
            self._running = False
        elif key == pygame.K_SPACE:
            self._face.do_blink()
        elif key == pygame.K_LEFT:
            self._face.look_left()
        elif key == pygame.K_RIGHT:
            self._face.look_right()
        elif key == pygame.K_UP:
            self._face.look_up()
        elif key == pygame.K_DOWN:
            self._face.look_down()
        elif key == pygame.K_HOME:
            self._face.look_front()
        elif key == pygame.K_r:
            self._face.random_look = not self._face.random_look
        elif key == pygame.K_b:
            self._face.random_blink = not self._face.random_blink
        elif key in key_emotions:
            self._face.set_emotion(key_emotions[key])

    def run(self):
        """Run display in current thread (blocking)."""
        self._main_loop()

    def start(self):
        """Start display in background thread."""
        if self._thread is not None and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._main_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop the display."""
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None

    def is_running(self) -> bool:
        """Check if display is running."""
        return self._running

    def send_command(self, cmd: Callable, *args, **kwargs):
        """Send a command to be executed in the display thread."""
        self._command_queue.put((cmd, args, kwargs))

    # Public API for MCP
    def set_emotion(self, emotion: str):
        """Set emotion (thread-safe)."""
        if self._face:
            self.send_command(self._face.set_emotion, emotion)

    def look_at(self, x: float, y: float):
        """Set look direction (thread-safe)."""
        if self._face:
            self.send_command(self._face.look_at, x, y)

    def blink(self):
        """Trigger blink (thread-safe)."""
        if self._face:
            self.send_command(self._face.do_blink)

    def set_eye_color(self, r: int, g: int, b: int):
        """Set eye color (thread-safe)."""
        if self._renderer:
            self.send_command(self._renderer.set_eye_color, r, g, b)

    def set_random_look(self, enabled: bool):
        """Enable/disable random look."""

        def _set():
            if self._face:
                self._face.random_look = enabled

        self.send_command(_set)

    def set_random_blink(self, enabled: bool):
        """Enable/disable random blink."""

        def _set():
            if self._face:
                self._face.random_blink = enabled

        self.send_command(_set)

    def get_state(self) -> dict:
        """Get current state."""
        if self._face:
            return self._face.get_state()
        return {}

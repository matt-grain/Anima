# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
Face class with two eyes and behaviors.
"""

import random
from .eye import Eye, Transformation
from .renderer import EyeRenderer
from .animations import AsyncTimer
from .presets import (
    Emotion,
    EMOTION_NAMES,
    emotion_from_name,
    PRESET_NORMAL,
    PRESET_ANGRY,
    PRESET_GLEE,
    PRESET_HAPPY,
    PRESET_SAD,
    PRESET_WORRIED,
    PRESET_WORRIED_ALT,
    PRESET_FOCUSED,
    PRESET_ANNOYED,
    PRESET_ANNOYED_ALT,
    PRESET_SURPRISED,
    PRESET_SKEPTIC,
    PRESET_SKEPTIC_ALT,
    PRESET_FRUSTRATED,
    PRESET_UNIMPRESSED,
    PRESET_UNIMPRESSED_ALT,
    PRESET_SLEEPY,
    PRESET_SLEEPY_ALT,
    PRESET_SUSPICIOUS,
    PRESET_SUSPICIOUS_ALT,
    PRESET_SQUINT,
    PRESET_SQUINT_ALT,
    PRESET_FURIOUS,
    PRESET_SCARED,
    PRESET_AWE,
)
from .config import Config


class BlinkAssistant:
    """Automatic blinking."""

    def __init__(self, face: "Face", interval_ms: int = 3500):
        self._face = face
        self.timer = AsyncTimer(interval_ms)
        self.timer.start()

    def update(self):
        self.timer.update()
        if self.timer.is_expired():
            self.blink()

    def blink(self):
        self._face.left_eye.blink_transformation.animation.restart()
        self._face.right_eye.blink_transformation.animation.restart()
        self.timer.reset()


class LookAssistant:
    """Random and controlled look direction."""

    def __init__(self, face: "Face", interval_ms: int = 4000):
        self._face = face
        self.timer = AsyncTimer(interval_ms)
        self.timer.start()
        self._current_x = 0.0
        self._current_y = 0.0

    def look_at(self, x: float, y: float):
        """Look at position (-1 to 1 for both axes)."""
        self._current_x = max(-1.0, min(1.0, x))
        self._current_y = max(-1.0, min(1.0, y))

        move_x_x = -25 * x
        move_y_y = 20 * y
        scale_y_x = 1.0 - x * 0.2
        scale_y_y = 1.0 - abs(y) * 0.4

        # Right eye transform
        right_transform = Transformation()
        right_transform.move_x = move_x_x
        right_transform.move_y = move_y_y
        right_transform.scale_x = 1.0
        right_transform.scale_y = scale_y_x * scale_y_y
        self._face.right_eye.transformation.set_destin(right_transform)

        # Left eye transform
        left_transform = Transformation()
        left_transform.move_x = move_x_x
        left_transform.move_y = move_y_y
        left_transform.scale_x = 1.0
        scale_y_x_left = 1.0 + x * 0.2
        left_transform.scale_y = scale_y_x_left * scale_y_y
        self._face.left_eye.transformation.set_destin(left_transform)

        self._face.right_eye.transformation.animation.restart()
        self._face.left_eye.transformation.animation.restart()

    def update(self):
        self.timer.update()
        if self.timer.is_expired():
            self.timer.reset()
            x = random.randint(-50, 50) / 100.0
            y = random.randint(-50, 50) / 100.0
            self.look_at(x, y)

    @property
    def current_position(self) -> tuple[float, float]:
        return (self._current_x, self._current_y)


class FaceExpression:
    """Expression transitions."""

    def __init__(self, face: "Face"):
        self._face = face

    def clear_variations(self):
        self._face.right_eye.variation1.clear()
        self._face.right_eye.variation2.clear()
        self._face.left_eye.variation1.clear()
        self._face.left_eye.variation2.clear()
        self._face.right_eye.variation1.animation.restart()
        self._face.left_eye.variation1.animation.restart()

    def go_to_normal(self):
        self.clear_variations()
        self._face.right_eye.variation1.values.height = 3
        self._face.right_eye.variation2.values.width = 1
        self._face.left_eye.variation1.values.height = 2
        self._face.left_eye.variation2.values.width = 2
        self._face.right_eye.variation1.animation.set_triangle(1000, 0)
        self._face.left_eye.variation1.animation.set_triangle(1000, 0)
        self._face.right_eye.transition_to(PRESET_NORMAL)
        self._face.left_eye.transition_to(PRESET_NORMAL)

    def go_to_angry(self):
        self.clear_variations()
        self._face.right_eye.variation1.values.offset_y = 2
        self._face.left_eye.variation1.values.offset_y = 2
        self._face.right_eye.variation1.animation.set_triangle(300, 0)
        self._face.left_eye.variation1.animation.set_triangle(300, 0)
        self._face.right_eye.transition_to(PRESET_ANGRY)
        self._face.left_eye.transition_to(PRESET_ANGRY)

    def go_to_glee(self):
        self.clear_variations()
        self._face.right_eye.variation1.values.offset_y = 5
        self._face.left_eye.variation1.values.offset_y = 5
        self._face.right_eye.variation1.animation.set_triangle(300, 0)
        self._face.left_eye.variation1.animation.set_triangle(300, 0)
        self._face.right_eye.transition_to(PRESET_GLEE)
        self._face.left_eye.transition_to(PRESET_GLEE)

    def go_to_happy(self):
        self.clear_variations()
        self._face.right_eye.transition_to(PRESET_HAPPY)
        self._face.left_eye.transition_to(PRESET_HAPPY)

    def go_to_sad(self):
        self.clear_variations()
        self._face.right_eye.transition_to(PRESET_SAD)
        self._face.left_eye.transition_to(PRESET_SAD)

    def go_to_worried(self):
        self.clear_variations()
        self._face.right_eye.transition_to(PRESET_WORRIED)
        self._face.left_eye.transition_to(PRESET_WORRIED_ALT)

    def go_to_focused(self):
        self.clear_variations()
        self._face.right_eye.transition_to(PRESET_FOCUSED)
        self._face.left_eye.transition_to(PRESET_FOCUSED)

    def go_to_annoyed(self):
        self.clear_variations()
        self._face.right_eye.transition_to(PRESET_ANNOYED)
        self._face.left_eye.transition_to(PRESET_ANNOYED_ALT)

    def go_to_surprised(self):
        self.clear_variations()
        self._face.right_eye.transition_to(PRESET_SURPRISED)
        self._face.left_eye.transition_to(PRESET_SURPRISED)

    def go_to_skeptic(self):
        self.clear_variations()
        self._face.right_eye.transition_to(PRESET_SKEPTIC)
        self._face.left_eye.transition_to(PRESET_SKEPTIC_ALT)

    def go_to_frustrated(self):
        self.clear_variations()
        self._face.right_eye.transition_to(PRESET_FRUSTRATED)
        self._face.left_eye.transition_to(PRESET_FRUSTRATED)

    def go_to_unimpressed(self):
        self.clear_variations()
        self._face.right_eye.transition_to(PRESET_UNIMPRESSED)
        self._face.left_eye.transition_to(PRESET_UNIMPRESSED_ALT)

    def go_to_sleepy(self):
        self.clear_variations()
        self._face.right_eye.transition_to(PRESET_SLEEPY)
        self._face.left_eye.transition_to(PRESET_SLEEPY_ALT)

    def go_to_suspicious(self):
        self.clear_variations()
        self._face.right_eye.transition_to(PRESET_SUSPICIOUS)
        self._face.left_eye.transition_to(PRESET_SUSPICIOUS_ALT)

    def go_to_squint(self):
        self.clear_variations()
        self._face.left_eye.variation1.values.offset_x = 6
        self._face.left_eye.variation2.values.offset_y = 6
        self._face.right_eye.transition_to(PRESET_SQUINT)
        self._face.left_eye.transition_to(PRESET_SQUINT_ALT)

    def go_to_furious(self):
        self.clear_variations()
        self._face.right_eye.transition_to(PRESET_FURIOUS)
        self._face.left_eye.transition_to(PRESET_FURIOUS)

    def go_to_scared(self):
        self.clear_variations()
        self._face.right_eye.transition_to(PRESET_SCARED)
        self._face.left_eye.transition_to(PRESET_SCARED)

    def go_to_awe(self):
        self.clear_variations()
        self._face.right_eye.transition_to(PRESET_AWE)
        self._face.left_eye.transition_to(PRESET_AWE)


class Face:
    """Main face class with two eyes and behaviors."""

    def __init__(self, config: Config | None = None):
        if config is None:
            config = Config()
        self._config = config

        self.width = config.display.width
        self.height = config.display.height
        self.eye_size = config.eye_shape.eye_size
        self.eye_spacing = config.eye_shape.eye_spacing

        self.center_x = self.width // 2
        self.center_y = self.height // 2

        # Create eyes with speed settings
        anim = config.animation
        self.left_eye = Eye(
            anim.transition_speed,
            anim.look_speed,
            anim.blink_speed,
            anim.variation_speed,
        )
        self.right_eye = Eye(
            anim.transition_speed,
            anim.look_speed,
            anim.blink_speed,
            anim.variation_speed,
        )
        self.left_eye.is_mirrored = True

        # Create assistants
        self.blink = BlinkAssistant(self, config.behavior.blink_interval_ms)
        self.look = LookAssistant(self, config.behavior.look_interval_ms)
        self.expression = FaceExpression(self)

        # Behavior flags
        self.random_behavior = config.behavior.random_behavior
        self.random_look = config.behavior.random_look
        self.random_blink = config.behavior.random_blink

        # Current state
        self.current_emotion = Emotion.NORMAL

    def update(self):
        """Update face state (call each frame)."""
        if self.random_look:
            self.look.update()
        if self.random_blink:
            self.blink.update()

    def draw(self, renderer: EyeRenderer):
        """Draw face to renderer."""
        # Position eyes
        self.left_eye.center_x = self.center_x - self.eye_size // 2 - self.eye_spacing
        self.left_eye.center_y = self.center_y
        self.right_eye.center_x = self.center_x + self.eye_size // 2 + self.eye_spacing
        self.right_eye.center_y = self.center_y

        # Draw eyes
        self.left_eye.draw(renderer)
        self.right_eye.draw(renderer)

    def do_blink(self):
        """Trigger a blink."""
        self.blink.blink()

    def look_at(self, x: float, y: float):
        """Look at position (-1 to 1)."""
        self.look.look_at(x, y)

    def look_left(self):
        self.look.look_at(1.0, 0.0)

    def look_right(self):
        self.look.look_at(-1.0, 0.0)

    def look_front(self):
        self.look.look_at(0.0, 0.0)

    def look_up(self):
        self.look.look_at(0.0, 1.0)

    def look_down(self):
        self.look.look_at(0.0, -1.0)

    def set_emotion(self, emotion: Emotion | str):
        """Set current emotion."""
        if isinstance(emotion, str):
            emotion = emotion_from_name(emotion)

        self.current_emotion = emotion
        expressions = {
            Emotion.NORMAL: self.expression.go_to_normal,
            Emotion.ANGRY: self.expression.go_to_angry,
            Emotion.GLEE: self.expression.go_to_glee,
            Emotion.HAPPY: self.expression.go_to_happy,
            Emotion.SAD: self.expression.go_to_sad,
            Emotion.WORRIED: self.expression.go_to_worried,
            Emotion.FOCUSED: self.expression.go_to_focused,
            Emotion.ANNOYED: self.expression.go_to_annoyed,
            Emotion.SURPRISED: self.expression.go_to_surprised,
            Emotion.SKEPTIC: self.expression.go_to_skeptic,
            Emotion.FRUSTRATED: self.expression.go_to_frustrated,
            Emotion.UNIMPRESSED: self.expression.go_to_unimpressed,
            Emotion.SLEEPY: self.expression.go_to_sleepy,
            Emotion.SUSPICIOUS: self.expression.go_to_suspicious,
            Emotion.SQUINT: self.expression.go_to_squint,
            Emotion.FURIOUS: self.expression.go_to_furious,
            Emotion.SCARED: self.expression.go_to_scared,
            Emotion.AWE: self.expression.go_to_awe,
        }
        if emotion in expressions:
            expressions[emotion]()

    def get_state(self) -> dict:
        """Get current face state."""
        return {
            "emotion": EMOTION_NAMES[self.current_emotion],
            "look_position": self.look.current_position,
            "random_look": self.random_look,
            "random_blink": self.random_blink,
        }

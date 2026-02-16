# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
Eye class with transformation pipeline.
"""

from .eye_config import EyeConfig
from .animations import RampAnimation, TrapeziumAnimation, TrapeziumPulseAnimation
from .renderer import EyeRenderer


class EyeTransition:
    """Handles smooth transition between eye configs."""

    def __init__(self, speed_multiplier: float = 1.0):
        self.origin: EyeConfig | None = None
        self.start = EyeConfig()
        self.destin = EyeConfig()
        self.animation = RampAnimation(500, speed_multiplier)

    def restart(self):
        if self.origin:
            self.start.offset_x = self.origin.offset_x
            self.start.offset_y = self.origin.offset_y
            self.start.height = self.origin.height
            self.start.width = self.origin.width
            self.start.slope_top = self.origin.slope_top
            self.start.slope_bottom = self.origin.slope_bottom
            self.start.radius_top = self.origin.radius_top
            self.start.radius_bottom = self.origin.radius_bottom
        self.animation.restart()

    def update(self):
        t = self.animation.get_value()
        self.apply(t)

    def apply(self, t: float):
        if self.origin is None:
            return
        self.origin.offset_x = int(self.start.offset_x * (1 - t) + self.destin.offset_x * t)
        self.origin.offset_y = int(self.start.offset_y * (1 - t) + self.destin.offset_y * t)
        self.origin.height = int(self.start.height * (1 - t) + self.destin.height * t)
        self.origin.width = int(self.start.width * (1 - t) + self.destin.width * t)
        self.origin.slope_top = self.start.slope_top * (1 - t) + self.destin.slope_top * t
        self.origin.slope_bottom = self.start.slope_bottom * (1 - t) + self.destin.slope_bottom * t
        self.origin.radius_top = int(self.start.radius_top * (1 - t) + self.destin.radius_top * t)
        self.origin.radius_bottom = int(self.start.radius_bottom * (1 - t) + self.destin.radius_bottom * t)


class Transformation:
    """Movement and scale transformation."""

    def __init__(self):
        self.move_x: float = 0.0
        self.move_y: float = 0.0
        self.scale_x: float = 1.0
        self.scale_y: float = 1.0


class EyeTransformation:
    """Handles eye position and scale transformations."""

    def __init__(self, speed_multiplier: float = 1.0):
        self.input: EyeConfig | None = None
        self.output = EyeConfig()
        self.start = Transformation()
        self.current = Transformation()
        self.destin = Transformation()
        self.animation = RampAnimation(200, speed_multiplier)

    def update(self):
        t = self.animation.get_value()
        self.current.move_x = (self.destin.move_x - self.start.move_x) * t + self.start.move_x
        self.current.move_y = (self.destin.move_y - self.start.move_y) * t + self.start.move_y
        self.current.scale_x = (self.destin.scale_x - self.start.scale_x) * t + self.start.scale_x
        self.current.scale_y = (self.destin.scale_y - self.start.scale_y) * t + self.start.scale_y
        self.apply()

    def apply(self):
        if self.input is None:
            return
        self.output.offset_x = int(self.input.offset_x + self.current.move_x)
        self.output.offset_y = int(self.input.offset_y - self.current.move_y)
        self.output.width = int(self.input.width * self.current.scale_x)
        self.output.height = int(self.input.height * self.current.scale_y)
        self.output.slope_top = self.input.slope_top
        self.output.slope_bottom = self.input.slope_bottom
        self.output.radius_top = self.input.radius_top
        self.output.radius_bottom = self.input.radius_bottom

    def set_destin(self, transformation: Transformation):
        self.start.move_x = self.current.move_x
        self.start.move_y = self.current.move_y
        self.start.scale_x = self.current.scale_x
        self.start.scale_y = self.current.scale_y
        self.destin.move_x = transformation.move_x
        self.destin.move_y = transformation.move_y
        self.destin.scale_x = transformation.scale_x
        self.destin.scale_y = transformation.scale_y


class EyeVariation:
    """Adds subtle variations to eye config."""

    def __init__(self, speed_multiplier: float = 1.0):
        self.input: EyeConfig | None = None
        self.output = EyeConfig()
        self.values = EyeConfig()
        self.clear()
        self.animation = TrapeziumPulseAnimation(0, 1000, 0, 1000, 0, speed_multiplier)

    def clear(self):
        self.values.offset_x = 0
        self.values.offset_y = 0
        self.values.height = 0
        self.values.width = 0
        self.values.slope_top = 0
        self.values.slope_bottom = 0
        self.values.radius_top = 0
        self.values.radius_bottom = 0
        self.values.inverse_radius_top = 0
        self.values.inverse_radius_bottom = 0
        self.values.inverse_offset_top = 0
        self.values.inverse_offset_bottom = 0

    def update(self):
        t = self.animation.get_value()
        self.apply(2.0 * t - 1.0)

    def apply(self, t: float):
        if self.input is None:
            return
        self.output.offset_x = int(self.input.offset_x + self.values.offset_x * t)
        self.output.offset_y = int(self.input.offset_y + self.values.offset_y * t)
        self.output.height = int(self.input.height + self.values.height * t)
        self.output.width = int(self.input.width + self.values.width * t)
        self.output.slope_top = self.input.slope_top + self.values.slope_top * t
        self.output.slope_bottom = self.input.slope_bottom + self.values.slope_bottom * t
        self.output.radius_top = int(self.input.radius_top + self.values.radius_top * t)
        self.output.radius_bottom = int(self.input.radius_bottom + self.values.radius_bottom * t)


class EyeBlink:
    """Handles blink animation."""

    def __init__(self, speed_multiplier: float = 1.0):
        self.input: EyeConfig | None = None
        self.output = EyeConfig()
        self.animation = TrapeziumAnimation(40, 100, 40, speed_multiplier)
        self.blink_width = 60
        self.blink_height = 2

    def update(self):
        t = self.animation.get_value()
        if self.animation.get_elapsed() > self.animation.interval:
            t = 0.0
        self.apply(t * t)

    def apply(self, t: float):
        if self.input is None:
            return
        self.output.offset_x = self.input.offset_x
        self.output.offset_y = self.input.offset_y
        self.output.width = int((self.blink_width - self.input.width) * t + self.input.width)
        self.output.height = int((self.blink_height - self.input.height) * t + self.input.height)
        self.output.slope_top = self.input.slope_top * (1.0 - t)
        self.output.slope_bottom = self.input.slope_bottom * (1.0 - t)
        self.output.radius_top = int(self.input.radius_top * (1.0 - t))
        self.output.radius_bottom = int(self.input.radius_bottom * (1.0 - t))


class Eye:
    """A single eye with transformation pipeline."""

    def __init__(self, transition_speed: float = 1.0, look_speed: float = 1.0, blink_speed: float = 1.0, variation_speed: float = 1.0):
        self.center_x = 0
        self.center_y = 0
        self.is_mirrored = False

        self.config = EyeConfig()
        self.transition = EyeTransition(transition_speed)
        self.transformation = EyeTransformation(look_speed)
        self.variation1 = EyeVariation(variation_speed)
        self.variation2 = EyeVariation(variation_speed)
        self.blink_transformation = EyeBlink(blink_speed)

        # Chain the operators
        self.transition.origin = self.config
        self.transformation.input = self.config
        self.variation1.input = self.transformation.output
        self.variation2.input = self.variation1.output
        self.blink_transformation.input = self.variation2.output
        self.final_config = self.blink_transformation.output

        # Set up variation animations
        self.variation1.animation._t0 = 200
        self.variation1.animation._t1 = 200
        self.variation1.animation._t2 = 200
        self.variation1.animation._t3 = 200
        self.variation1.animation._t4 = 0

        self.variation2.animation._t0 = 0
        self.variation2.animation._t1 = 200
        self.variation2.animation._t2 = 200
        self.variation2.animation._t3 = 200
        self.variation2.animation._t4 = 200

    def update(self):
        self.transition.update()
        self.transformation.update()
        self.variation1.update()
        self.variation2.update()
        self.blink_transformation.update()

    def draw(self, renderer: EyeRenderer):
        self.update()
        renderer.draw_eye(self.center_x, self.center_y, self.final_config)

    def transition_to(self, preset: EyeConfig):
        self.transition.destin.offset_x = -preset.offset_x if self.is_mirrored else preset.offset_x
        self.transition.destin.offset_y = -preset.offset_y
        self.transition.destin.height = preset.height
        self.transition.destin.width = preset.width
        self.transition.destin.slope_top = preset.slope_top if self.is_mirrored else -preset.slope_top
        self.transition.destin.slope_bottom = preset.slope_bottom if self.is_mirrored else -preset.slope_bottom
        self.transition.destin.radius_top = preset.radius_top
        self.transition.destin.radius_bottom = preset.radius_bottom
        self.transition.restart()

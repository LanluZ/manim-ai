from __future__ import annotations


def generate_fast_template_scene(prompt: str) -> str:
    title = _escape(prompt[:28] or "Math preview")
    return f'''from manim import *

class FastPreviewScene(Scene):
    def construct(self):
        title = Text("{title}", font_size=18).to_edge(UP)
        x_axis = Line(LEFT * 2.8, RIGHT * 2.8, color=GRAY)
        y_axis = Line(DOWN * 1.1, UP * 1.1, color=GRAY)
        graph = VMobject(color=BLUE)
        points = [
            LEFT * 2.4 + DOWN * 0.6,
            LEFT * 1.2 + UP * 0.4,
            ORIGIN + DOWN * 0.1,
            RIGHT * 1.2 + UP * 0.7,
            RIGHT * 2.4 + DOWN * 0.2,
        ]
        graph.set_points_smoothly(points)
        dot = Dot(points[-2], color=YELLOW, radius=0.06)
        label = Text("key point", font_size=14).next_to(dot, UP, buff=0.08)
        self.add(title, x_axis, y_axis, graph, dot, label)
        self.play(dot.animate.scale(1.4), run_time=0.2)
        self.wait(0.1)
'''


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")

import numpy as np
import moderngl
import pygame
from typing import Optional, Tuple

SCREEN_VS = """
#version 330 core
in vec2 in_vert;
in vec2 in_uv;
out vec2 v_uv;
void main() {
    v_uv = in_uv;
    gl_Position = vec4(in_vert, 0.0, 1.0);
}
"""

SCREEN_FS = """
#version 330 core
uniform sampler2D u_texture;
uniform float u_brightness;
uniform mat3 u_color_matrix;
uniform float u_color_intensity;

in vec2 v_uv;
out vec4 fragColor;

void main() {
    vec4 tex = texture(u_texture, v_uv);
    vec3 col = tex.rgb;

    // Daltonismo (Brettel / Machado)
    if (u_color_intensity > 0.0) {
        vec3 simulated = u_color_matrix * col;
        col = mix(col, simulated, u_color_intensity);
    }

    // Brillo en GLSL
    if (u_brightness < 1.0) {
        col *= u_brightness;
    } else if (u_brightness > 1.0) {
        col = mix(col, vec3(1.0), (u_brightness - 1.0) * 0.5);
    }

    fragColor = vec4(col, tex.a);
}
"""

PARTICLE_VS = """
#version 330 core
in vec2 in_quad;

in vec2 in_pos;        // Posición virtual (0..1920, 0..1080)
in vec2 in_size;       // Tamaño (w, h)
in float in_rot_z;     // Rotación Z (rad)
in float in_rot_y;     // Volteo 3D Y (rad)
in vec4 in_color;      // Color RGBA

uniform vec2 u_virtual_res; // (1920.0, 1080.0)
uniform float u_time;

out vec2 v_uv;
out vec4 v_color;

void main() {
    v_uv = in_quad;
    v_color = in_color;

    // Curvatura por viento
    float wave = sin(u_time * 3.5 + in_pos.x * 0.015 + in_pos.y * 0.015) * 0.2;
    vec2 local = in_quad;
    local.x += wave * local.y;

    // Volteo 3D
    local.x *= cos(in_rot_y);

    // Rotación planar Z
    float cz = cos(in_rot_z);
    float sz = sin(in_rot_z);
    mat2 rot_mat = mat2(cz, -sz, sz, cz);
    vec2 rotated = rot_mat * (local * in_size);

    vec2 world_pos = in_pos + rotated;

    // Conversión a NDC (-1 a 1)
    vec2 ndc;
    ndc.x = (world_pos.x / u_virtual_res.x) * 2.0 - 1.0;
    ndc.y = 1.0 - (world_pos.y / u_virtual_res.y) * 2.0;

    gl_Position = vec4(ndc, 0.0, 1.0);
}
"""

PARTICLE_FS = """
#version 330 core
in vec2 v_uv;
in vec4 v_color;
out vec4 fragColor;

void main() {
    vec2 p = v_uv * 2.0;
    float d = (p.x * p.x) + (p.y * p.y);
    float alpha_mask = smoothstep(1.0, 0.72, d);
    if (alpha_mask <= 0.01) {
        discard;
    }

    float highlight = smoothstep(0.7, 0.0, abs(p.x));
    vec3 col = mix(v_color.rgb * 0.9, v_color.rgb * 1.15, highlight * 0.45);

    fragColor = vec4(col, v_color.a * alpha_mask);
}
"""

class GLRenderer:
    """
    Pipeline híbrido Pygame 2D + ModernGL Shaders a resolución Full HD (1920x1080):
    1. Renderiza la escena base 2D como textura con Letterbox / Pillarbox dinámico.
    2. Renderiza partículas de pétalos con Shaders GLSL acelerados por GPU.
    """
    def __init__(self, virtual_w: int = 1920, virtual_h: int = 1080) -> None:
        self.virtual_w = virtual_w
        self.virtual_h = virtual_h
        self.ctx = moderngl.create_context()

        # Habilitar Alpha Blending
        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = (moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA)

        # 1. Pipeline de Textura Pygame 2D
        self.screen_prog = self.ctx.program(vertex_shader=SCREEN_VS, fragment_shader=SCREEN_FS)
        screen_vertices = np.array([
            -1.0, -1.0,    0.0, 1.0,
             1.0, -1.0,    1.0, 1.0,
            -1.0,  1.0,    0.0, 0.0,
             1.0,  1.0,    1.0, 0.0,
        ], dtype='f4')
        self.screen_vbo = self.ctx.buffer(screen_vertices.tobytes())
        self.screen_vao = self.ctx.vertex_array(
            self.screen_prog,
            [(self.screen_vbo, '2f 2f', 'in_vert', 'in_uv')]
        )
        self.screen_texture = self.ctx.texture((virtual_w, virtual_h), 4)
        self.screen_texture.filter = (moderngl.LINEAR, moderngl.LINEAR)

        # 2. Pipeline de Partículas GLSL
        self.particle_prog = self.ctx.program(vertex_shader=PARTICLE_VS, fragment_shader=PARTICLE_FS)
        self.particle_prog['u_virtual_res'].value = (float(virtual_w), float(virtual_h))

        quad_verts = np.array([
            -0.5, -0.5,
             0.5, -0.5,
            -0.5,  0.5,
             0.5,  0.5,
        ], dtype='f4')
        self.quad_vbo = self.ctx.buffer(quad_verts.tobytes())

        self.max_particles = 128
        self.instance_vbo = self.ctx.buffer(reserve=self.max_particles * 40, dynamic=True)
        self.particle_vao = self.ctx.vertex_array(
            self.particle_prog,
            [
                (self.quad_vbo, '2f', 'in_quad'),
                (self.instance_vbo, '2f 2f 1f 1f 4f /i', 'in_pos', 'in_size', 'in_rot_z', 'in_rot_y', 'in_color')
            ]
        )

        self.vp_x = 0
        self.vp_y = 0
        self.vp_w = virtual_w
        self.vp_h = virtual_h
        self.scale = 1.0

    def compute_viewport(self, win_w: int, win_h: int) -> Tuple[int, int, int, int]:
        """Calcula el viewport con Letterbox / Pillarbox preservando el ratio 16:9 estricto."""
        scale_x = win_w / self.virtual_w
        scale_y = win_h / self.virtual_h
        self.scale = min(scale_x, scale_y)

        self.vp_w = int(self.virtual_w * self.scale)
        self.vp_h = int(self.virtual_h * self.scale)
        self.vp_x = (win_w - self.vp_w) // 2
        self.vp_y = (win_h - self.vp_h) // 2
        return self.vp_x, self.vp_y, self.vp_w, self.vp_h

    def screen_to_virtual(self, screen_x: int, screen_y: int) -> Tuple[int, int]:
        """Convierte coordenadas reales de la ventana a coordenadas virtuales (1920x1080)."""
        if self.scale <= 0.0:
            return screen_x, screen_y
        virt_x = int((screen_x - self.vp_x) / self.scale)
        virt_y = int((screen_y - self.vp_y) / self.scale)
        return virt_x, virt_y

    def render_frame(
        self,
        pygame_surface: pygame.Surface,
        particle_instance_data: bytes,
        particle_count: int,
        time_seconds: float,
        win_w: int,
        win_h: int,
        brightness: float = 1.0,
        color_matrix: Optional[np.ndarray] = None,
        color_intensity: float = 0.0
    ) -> None:
        """Renderiza la escena completa a través de ModernGL a 1080p con Letterbox y post-procesado GLSL."""
        vx, vy, vw, vh = self.compute_viewport(win_w, win_h)
        self.ctx.viewport = (0, 0, win_w, win_h)
        self.ctx.clear(0.04, 0.04, 0.06, 1.0)

        gl_vy = win_h - vy - vh
        self.ctx.viewport = (vx, gl_vy, vw, vh)

        raw_bytes = pygame.image.tostring(pygame_surface, 'RGBA', False)
        self.screen_texture.write(raw_bytes)
        self.screen_texture.use(location=0)
        self.screen_prog['u_texture'].value = 0

        # Uniforms de post-procesado visual en GPU (0% overhead CPU)
        if 'u_brightness' in self.screen_prog:
            self.screen_prog['u_brightness'].value = float(brightness)
        if 'u_color_intensity' in self.screen_prog:
            self.screen_prog['u_color_intensity'].value = float(color_intensity)
        if 'u_color_matrix' in self.screen_prog and color_matrix is not None:
            # GLSL espera matriz en orden column-major como tupla plana
            self.screen_prog['u_color_matrix'].value = tuple(color_matrix.T.flatten())

        self.screen_vao.render(moderngl.TRIANGLE_STRIP)

        if particle_count > 0:
            self.particle_prog['u_time'].value = time_seconds
            self.instance_vbo.write(particle_instance_data[:particle_count * 40])
            self.particle_vao.render(moderngl.TRIANGLE_STRIP, instances=particle_count)

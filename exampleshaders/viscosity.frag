#version 330 core
out vec4 fragColor;
uniform float u_time;
uniform vec2 u_resolution;
uniform vec4 u_mouse;
uniform int u_frame;

#define AA 2

void main() {
    vec4 finalColor = vec4(0.0);
    for (int aa = 0; aa < AA; aa++) {
        vec2 offset = vec2(0.0);
        if (AA > 1) {
            float angle = 6.28318 * (float(aa) + 0.5) / float(AA);
            offset = vec2(cos(angle), sin(angle)) * 0.5;
        }
        vec2 fragCoord = gl_FragCoord.xy + offset;
        vec2 uv = fragCoord / u_resolution.y * 4.0 + u_resolution.xy / u_resolution.y;
        vec2 c = uv;
        vec2 s = floor(c);

        for (int i = 1; i < 9; i++) {
            c += cos(float(i) * c.yx + 0.1 / (s - c) + u_time) / float(i);
        }

        vec4 v = abs(sin(c.y + vec4(0.0, 0.4, 0.2, 0.0)));
        finalColor += exp(-3.0 * v);
    }
    finalColor /= float(AA);
    fragColor = finalColor;
}

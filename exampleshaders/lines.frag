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
        vec2 p = (fragCoord * 2.0 - u_resolution.xy) / u_resolution.y * 2.0;
        p += sin(p.yx * 3.0 + u_time * 0.1) * 0.6;

        float d = length(p);
        float v = 0.0;

        for (float k = 1.0; k < 4.0; k++) {
            vec2 q = fract(p * k * 0.7 + k * 2.0) - 0.5;
            float a = atan(q.y, q.x);
            float l = length(q);
            v += smoothstep(0.4, 0.0, abs(sin(a * 4.0 + l * 15.0 + u_time)));
        }

        vec4 bg = exp(-d * 5.0) * vec4(2.0, 1.5, 0.8, 0.0);
        vec4 fg = v * vec4(0.5, 0.7, 1.05, 1.0);
        finalColor += bg + fg;
    }
    finalColor /= float(AA);
    fragColor = finalColor;
}

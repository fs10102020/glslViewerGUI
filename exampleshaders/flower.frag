#version 330 core
out vec4 fragColor;
uniform float u_time;
uniform vec2 u_resolution;
uniform vec4 u_mouse;
uniform int u_frame;

#define AA 2

vec3 hsv(float h, float s, float v) {
    vec3 c = vec3(h, s, v);
    vec3 rgb = clamp(abs(mod(c.x * 6.0 + vec3(0, 4, 2), 6.0) - 3.0) - 1.0, 0.0, 1.0);
    return c.z * mix(vec3(1.0), rgb, c.y);
}

void main() {
    vec3 finalColor = vec3(0.0);
    for (int aa = 0; aa < AA; aa++) {
        vec2 offset = vec2(0.0);
        if (AA > 1) {
            float angle = 6.28318 * (float(aa) + 0.5) / float(AA);
            offset = vec2(cos(angle), sin(angle)) * 0.5;
        }
        vec2 fragCoord = gl_FragCoord.xy + offset;

        float t = u_time;
        vec3 col = vec3(0.0);

        vec3 d = vec3(fragCoord / u_resolution.xy * 0.4 + vec2(-0.2, 0.8), 1.0);
        vec3 q = vec3(0.0, -1.0, -1.0);

        float e = 0.0, R = 0.0;

        for (float i = 0.0; i < 80.0; i++) {
            vec3 p = q += d * e * R * 0.16;

            R = length(p);
            p = vec3(log2(R) - t * 0.5, exp(R - p.z / R * 0.1), atan(p.y, p.x));

            e = --p.y;
            float s;
            for (s = 7.0; s < 1000.0; s += s) {
                e += dot(sin(p.xz * s), sin(p.xx * s)) / s;
            }

            col -= hsv(R, 0.5, exp(-e) * 0.01) - vec3(exp(-e * 9.0) * 0.04);
        }

        finalColor += col;
    }
    finalColor /= float(AA);
    fragColor = vec4(finalColor, 1.0);
}

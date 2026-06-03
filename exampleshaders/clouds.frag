#version 330 core
out vec4 fragColor;
uniform float u_time;
uniform vec2 u_resolution;
uniform vec4 u_mouse;
uniform int u_frame;

#define AA 2

mat3 rotate3D(float angle, vec3 axis) {
    vec3 a = normalize(axis);
    float s = sin(angle);
    float c = cos(angle);
    float t = 1.0 - c;
    return mat3(
        c + a.x*a.x*t,        a.x*a.y*t - a.z*s,   a.x*a.z*t + a.y*s,
        a.y*a.x*t + a.z*s,    c + a.y*a.y*t,       a.y*a.z*t - a.x*s,
        a.z*a.x*t - a.y*s,    a.z*a.y*t + a.x*s,   c + a.z*a.z*t
    );
}

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
        float g = 0.0;

        for (float i = 0.0; i < 99.0; i++) {
            float e = 0.0, s = 0.0;

            vec3 p = vec3((fragCoord - 0.5 * u_resolution.xy) / u_resolution.y * 5.0 + vec2(0.0, 9.0), g);
            p *= rotate3D(-1.1 - cos(t * 0.15) * 0.1, vec3(1.0, 11.0 + sin(t) * 0.15, -1.5));

            s = 2.0;
            for (int j = 0; j < 19; j++) {
                e = 7.1 / dot(p, p * 0.51);
                s *= e;
                p = vec3(0.08, 4.0, -1.0) - abs(abs(p) * e - vec3(3.0, 4.0, 3.0));
            }

            g += p.y / s;
            s = log2(s) / exp(e);

            col += 0.01 - hsv(0.1, g * 0.016 - e * 0.3, s / 200.0);
        }

        finalColor += col;
    }
    finalColor /= float(AA);
    fragColor = vec4(finalColor, 1.0);
}

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
        vec2 uv = (fragCoord - 0.5 * u_resolution.xy) / u_resolution.y;
        vec3 ro = vec3(0.0, 0.0, -3.0);
        vec3 rd = normalize(vec3(uv, 1.0));
        vec4 col = vec4(0.0);
        float t = u_time;

        float a = t * 0.2 + uv.y * 2.0;
        rd.xz *= mat2(cos(a), -sin(a), sin(a), cos(a));

        float z = 0.0;
        for (int i = 0; i < 60; i++) {
            vec3 p = ro + rd * z;
            p.z += 5.0 + cos(t);

            a = t + p.y * 0.25;
            p.xz *= mat2(cos(a), -sin(a), sin(a), cos(a));

            float d = 2.0;
            for (int j = 0; j < 6; j++) {
                d /= 0.8;
                p += cos((p.yzx - vec3(t, 0.0, 0.0) * 8.0) * d + t) / d;
            }

            d = 0.01 + abs(length(p.xz) + p.y * 0.3 - 1.0) / 9.0;
            z += d;

            col += (sin(p.y * 0.5 - vec4(0.0, 1.0, 2.0, 0.0)) + 1.1) / d;
        }

        col = tanh(col * 0.001);
        finalColor += col;
    }
    finalColor /= float(AA);
    fragColor = finalColor;
}

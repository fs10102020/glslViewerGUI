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
        vec2 uv = fragCoord / u_resolution.xy * 2.0 - 1.0;
        uv.x *= u_resolution.x / u_resolution.y;

        vec4 col = vec4(0.0);
        float t = u_time;

        for (float z = 0.0, d = 0.0, i = 0.0; i < 20.0; i++) {
            vec3 p = z * normalize(vec3(fragCoord * 2.0 - u_resolution.xy, u_resolution.y));
            p = vec3(atan(p.y / 0.2, p.x) * 2.0, p.z / 3.0, length(p.xy) - 5.0 - z * 0.2);

            for (d = 1.0; d < 7.0; d++) {
                p += sin(p.yzx * d + t + 0.3 * i) / d;
            }

            d = length(vec4(0.4 * cos(p) - 0.4, p.z));
            z += d;

            col += (cos(p.x + i * 0.4 + z + vec4(6.0, 1.0, 2.0, 0.0)) + 1.0) / d;
        }

        col = tanh(col * col * 0.0025);
        finalColor += col;
    }
    finalColor /= float(AA);
    fragColor = finalColor;
}

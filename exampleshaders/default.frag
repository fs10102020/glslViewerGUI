#version 330 core
in vec2 vUV;
out vec4 fragColor;

uniform float u_time;
uniform vec2 u_resolution;
uniform vec4 u_mouse;
uniform int u_frame;

#define AA 2

void main() {
    vec3 finalColor = vec3(0.0);
    for (int aa = 0; aa < AA; aa++) {
        vec2 offset = vec2(0.0);
        if (AA > 1) {
            float angle = 6.28318 * (float(aa) + 0.5) / float(AA);
            offset = vec2(cos(angle), sin(angle)) * 0.5;
        }
        vec2 fragCoord = gl_FragCoord.xy + offset;
        vec2 uv = (fragCoord - 0.5 * u_resolution.xy) / u_resolution.y;
        float t = u_time;

        float d = length(uv);
        vec3 col = vec3(0.0);

        col += 0.5 + 0.5 * cos(t + uv.xyx + vec3(0.0, 2.0, 4.0));
        col += 0.5 + 0.5 * cos(t * 0.7 - uv.yxy + vec3(2.0, 4.0, 0.0));
        col *= smoothstep(0.8, 0.0, d);

        finalColor += col;
    }
    finalColor /= float(AA);
    fragColor = vec4(finalColor, 1.0);
}

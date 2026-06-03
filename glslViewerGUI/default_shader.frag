#ifdef GL_ES
precision mediump float;
#endif

uniform vec2 u_resolution;
uniform float u_time;

void main() {
    vec2 st = gl_FragCoord.xy / u_resolution;
    vec3 color = vec3(
        0.5 + 0.5 * sin(st.x * 3.14159 * 2.0 + u_time),
        0.5 + 0.5 * sin(st.y * 3.14159 * 2.0 + u_time * 1.3),
        0.5 + 0.5 * sin((st.x + st.y) * 3.14159 * 2.0 + u_time * 0.7)
    );
    gl_FragColor = vec4(color, 1.0);
}

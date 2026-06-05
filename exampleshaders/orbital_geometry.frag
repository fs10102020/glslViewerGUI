#version 330 core

in vec2 vUV;
in vec2 vScreen;
out vec4 fragColor;

uniform float u_time;
uniform vec2 u_resolution;
uniform vec4 u_mouse;
uniform int u_frame;

#define AA 2
#define MAX_STEPS 86
#define MAX_DIST 18.0
#define SURF_DIST 0.0012

mat2 rot(float a) {
    float s = sin(a);
    float c = cos(a);
    return mat2(c, -s, s, c);
}

float hash21(vec2 p) {
    p = fract(p * vec2(123.34, 456.21));
    p += dot(p, p + 45.32);
    return fract(p.x * p.y);
}

float sdSphere(vec3 p, float r) {
    return length(p) - r;
}

float sdTorus(vec3 p, vec2 t) {
    vec2 q = vec2(length(p.xz) - t.x, p.y);
    return length(q) - t.y;
}

float sdOctahedron(vec3 p, float s) {
    p = abs(p);
    return (p.x + p.y + p.z - s) * 0.57735027;
}

float sdCapsule(vec3 p, vec3 a, vec3 b, float r) {
    vec3 pa = p - a;
    vec3 ba = b - a;
    float h = clamp(dot(pa, ba) / dot(ba, ba), 0.0, 1.0);
    return length(pa - ba * h) - r;
}

vec2 opU(vec2 a, vec2 b) {
    return a.x < b.x ? a : b;
}

vec2 mapScene(vec3 p) {
    float t = u_time;
    vec2 res = vec2(100.0, 0.0);

    vec3 q = p;
    q.xz *= rot(t * 0.28);
    q.xy *= rot(0.35 * sin(t * 0.37));

    float core = sdSphere(q, 0.37 + 0.035 * sin(t * 2.2 + q.y * 8.0));
    res = opU(res, vec2(core, 1.0));

    float crystal = max(sdOctahedron(q, 0.78), -sdSphere(q, 0.43));
    crystal += 0.025 * sin(18.0 * q.x + t) * sin(16.0 * q.y - t * 1.4) * sin(15.0 * q.z);
    res = opU(res, vec2(crystal, 2.0));

    vec3 r1 = p;
    r1.xz *= rot(t * 0.72);
    res = opU(res, vec2(sdTorus(r1, vec2(1.18, 0.020)), 3.0));

    vec3 r2 = p;
    r2.xy *= rot(1.5708);
    r2.xz *= rot(-t * 0.45 + 0.8);
    res = opU(res, vec2(sdTorus(r2, vec2(1.42, 0.014)), 4.0));

    vec3 r3 = p;
    r3.yz *= rot(1.5708);
    r3.xy *= rot(t * 0.33 + 1.7);
    res = opU(res, vec2(sdTorus(r3, vec2(1.66, 0.010)), 5.0));

    vec3 arm = q;
    float beam = sdCapsule(arm, vec3(-1.75, 0.0, 0.0), vec3(1.75, 0.0, 0.0), 0.015);
    beam = min(beam, sdCapsule(arm, vec3(0.0, -1.75, 0.0), vec3(0.0, 1.75, 0.0), 0.013));
    beam = min(beam, sdCapsule(arm, vec3(0.0, 0.0, -1.75), vec3(0.0, 0.0, 1.75), 0.013));
    res = opU(res, vec2(beam, 6.0));

    return res;
}

vec3 calcNormal(vec3 p) {
    vec2 e = vec2(0.0015, 0.0);
    return normalize(vec3(
        mapScene(p + e.xyy).x - mapScene(p - e.xyy).x,
        mapScene(p + e.yxy).x - mapScene(p - e.yxy).x,
        mapScene(p + e.yyx).x - mapScene(p - e.yyx).x
    ));
}

vec3 materialColor(float id, vec3 p, vec3 n) {
    vec3 cyan = vec3(0.03, 0.82, 1.00);
    vec3 amber = vec3(1.00, 0.52, 0.05);
    vec3 violet = vec3(0.74, 0.30, 1.00);

    if (id < 1.5) {
        return mix(cyan, vec3(1.0), 0.25 + 0.25 * sin(u_time * 4.0));
    }
    if (id < 2.5) {
        float facets = pow(abs(dot(n, normalize(vec3(0.6, 0.7, 0.25)))), 3.0);
        return mix(cyan * 0.55, violet, facets);
    }
    if (id < 5.5) {
        float pulse = 0.65 + 0.35 * sin(u_time * 3.0 + id * 1.7 + length(p) * 9.0);
        return mix(amber, cyan, smoothstep(3.0, 5.0, id)) * pulse;
    }
    return vec3(1.0, 0.78, 0.18);
}

vec2 march(vec3 ro, vec3 rd, out float glow) {
    float t = 0.0;
    float id = 0.0;
    glow = 0.0;

    for (int i = 0; i < MAX_STEPS; i++) {
        vec3 p = ro + rd * t;
        vec2 h = mapScene(p);
        glow += 0.010 / (0.030 + h.x * h.x * 70.0);
        if (h.x < SURF_DIST || t > MAX_DIST) {
            id = h.y;
            break;
        }
        t += h.x * 0.68;
    }

    return vec2(t, id);
}

float stars(vec2 uv) {
    vec2 gv = fract(uv) - 0.5;
    vec2 id = floor(uv);
    float rnd = hash21(id);
    float star = smoothstep(0.055, 0.0, length(gv - vec2(rnd - 0.5, fract(rnd * 17.31) - 0.5)));
    return star * step(0.965, rnd);
}

float hudRing(vec2 p, float r, float w) {
    return 1.0 - smoothstep(w, w + 0.004, abs(length(p) - r));
}

vec3 render(vec2 fragCoord) {
    vec2 uv = (fragCoord - 0.5 * u_resolution.xy) / u_resolution.y;
    float t = u_time;

    float mouseDown = step(0.5, u_mouse.z);
    float yaw = mix(t * 0.18, (u_mouse.x / max(u_resolution.x, 1.0) - 0.5) * 6.28318, mouseDown);
    float pitch = mix(0.28 + 0.12 * sin(t * 0.31), (u_mouse.y / max(u_resolution.y, 1.0) - 0.5) * 1.4, mouseDown);

    vec3 ro = vec3(0.0, 0.0, 4.5);
    ro.xz *= rot(yaw);
    ro.yz *= rot(pitch);

    vec3 ta = vec3(0.0);
    vec3 ww = normalize(ta - ro);
    vec3 uu = normalize(cross(vec3(0.0, 1.0, 0.0), ww));
    vec3 vv = cross(ww, uu);
    vec3 rd = normalize(uv.x * uu + uv.y * vv + 1.75 * ww);

    vec3 bg = vec3(0.006, 0.009, 0.015);
    bg += vec3(0.00, 0.10, 0.18) * pow(max(rd.y * 0.5 + 0.5, 0.0), 2.0);
    bg += vec3(1.00, 0.45, 0.05) * 0.07 * pow(max(-rd.y * 0.5 + 0.5, 0.0), 4.0);
    bg += stars(uv * 18.0 + t * 0.04) * vec3(0.9, 0.98, 1.0);
    bg += stars(uv * 37.0 - t * 0.03) * vec3(1.0, 0.58, 0.18) * 0.7;

    float glow;
    vec2 hit = march(ro, rd, glow);
    vec3 col = bg;

    if (hit.x < MAX_DIST) {
        vec3 p = ro + rd * hit.x;
        vec3 n = calcNormal(p);
        vec3 albedo = materialColor(hit.y, p, n);

        vec3 l1 = normalize(vec3(0.7, 1.1, 0.5));
        vec3 l2 = normalize(vec3(-0.8, -0.2, -0.7));
        float diff = max(dot(n, l1), 0.0);
        float fill = max(dot(n, l2), 0.0) * 0.35;
        float fresnel = pow(1.0 + dot(rd, n), 4.0);
        float spec = pow(max(dot(reflect(rd, n), l1), 0.0), 48.0);

        col = albedo * (0.14 + diff * 1.15 + fill);
        col += spec * vec3(1.0, 0.86, 0.55);
        col += fresnel * mix(vec3(0.0, 0.8, 1.0), vec3(1.0, 0.45, 0.02), smoothstep(2.0, 5.0, hit.y));
        col = mix(col, bg, smoothstep(6.0, MAX_DIST, hit.x));
    }

    vec3 aura = mix(vec3(0.0, 0.78, 1.0), vec3(1.0, 0.48, 0.02), 0.45 + 0.45 * sin(t * 0.9));
    col += aura * glow * 0.42;

    float scan = 0.5 + 0.5 * sin((uv.y + t * 0.12) * 700.0);
    col *= 0.94 + 0.035 * scan;

    float r0 = hudRing(uv, 0.72 + 0.03 * sin(t), 0.003);
    float r1 = hudRing(uv, 1.08, 0.002);
    float spokes = smoothstep(0.996, 1.0, cos(atan(uv.y, uv.x) * 24.0 + t * 0.9));
    spokes *= smoothstep(0.35, 1.05, length(uv)) * (1.0 - smoothstep(1.08, 1.11, length(uv)));
    col += (r0 * vec3(1.0, 0.48, 0.02) + r1 * vec3(0.0, 0.78, 1.0)) * 0.22;
    col += spokes * vec3(0.0, 0.55, 0.7) * 0.08;

    col = pow(max(col, 0.0), vec3(0.82));
    col *= 1.0 - 0.24 * dot(uv, uv);
    return col;
}

void main() {
    vec3 color = vec3(0.0);
    for (int aa = 0; aa < AA; aa++) {
        vec2 offset = vec2(0.0);
        if (AA > 1) {
            float a = 6.28318 * (float(aa) + 0.5) / float(AA);
            offset = vec2(cos(a), sin(a)) * 0.45;
        }
        color += render(gl_FragCoord.xy + offset);
    }
    color /= float(AA);
    fragColor = vec4(color, 1.0);
}

// ------------------------------------------------------------------
// SDF renderer common
// ------------------------------------------------------------------

#ifdef GL_ES
precision highp float;
#endif

// Scene hook forward declarations (filled in by user's scene.glsl)
float DE(vec3 p);
vec3 baseColor(vec3 p, vec3 normal);
vec3 emissionAt(vec3 p, vec3 normal);
void initScene();

uniform vec2 u_resolution;
uniform float u_time;
uniform int u_frame;
uniform vec2 u_mouse;
uniform float u_delta;

// glslViewer camera uniforms
uniform vec3 u_camera;
uniform mat4 u_viewMatrix;
uniform mat4 u_inverseViewMatrix;
uniform mat4 u_projectionMatrix;
uniform mat4 u_inverseProjectionMatrix;
uniform bool u_cameraChange;
uniform bool u_resolutionChange;
uniform float u_cameraFov;
uniform float u_cameraNearClip;
uniform float u_cameraFarClip;

// SDF renderer state
uniform int u_sceneRevision;

// Path-tracer accumulation targets (declared here so all pass variants
// share them; only the relevant #ifdef blocks actually sample them).
uniform sampler2D u_doubleBuffer0;
uniform sampler2D u_doubleBuffer1;

// Environment lighting state (used by preview and pathtrace)
uniform vec3 u_skyColor;
uniform vec3 u_horizonColor;
uniform vec3 u_groundColor;
uniform float u_envIntensity;
uniform vec3 u_sunDir;

// Display state
uniform float u_gamma;

// ------------------------------------------------------------------
// Math helpers
// ------------------------------------------------------------------

#define PI 3.141592653589793
#define TWO_PI 6.283185307179586
#define INF 1.0e20

float saturate(float x) { return clamp(x, 0.0, 1.0); }

vec2 saturate(vec2 x) { return clamp(x, 0.0, 1.0); }

vec3 saturate(vec3 x) { return clamp(x, 0.0, 1.0); }

vec3 environment(vec3 dir) {
    float t = saturate(dir.y * 0.5 + 0.5);
    vec3 col = mix(u_groundColor, mix(u_horizonColor, u_skyColor, t), t);
    return col * u_envIntensity;
}

float maxcomp(vec3 v) { return max(max(v.x, v.y), v.z); }

// Hash / RNG
// https://www.shadertoy.com/view/4djSRW
float hash(vec2 p) {
    vec3 p3 = fract(vec3(p.xyx) * 0.1031);
    p3 += dot(p3, p3.yzx + 33.33);
    return fract((p3.x + p3.y) * p3.z);
}

float hash(vec3 p) {
    vec3 p3 = fract(p * 0.1031);
    p3 += dot(p3, p3.yzx + 33.33);
    return fract((p3.x + p3.y) * p3.z);
}

vec2 hash2(vec2 p) {
    vec3 p3 = fract(vec3(p.xyx) * vec3(0.1031, 0.1030, 0.0973));
    p3 += dot(p3, p3.yzx + 33.33);
    return fract((p3.xx + p3.yz) * p3.zy);
}

vec3 hash3(vec3 p) {
    p = vec3(dot(p, vec3(127.1, 311.7, 74.7)),
             dot(p, vec3(269.5, 183.3, 246.1)),
             dot(p, vec3(113.5, 271.9, 124.6)));
    return fract(sin(p) * 43758.5453);
}

// PCG-style 2D random from integer state
uvec2 pcg2d(uvec2 v) {
    v = v * 1664525u + 1013904223u;
    v.x += v.y * 1664525u;
    v.y += v.x * 1664525u;
    v = v ^ (v >> 16u);
    v.x += v.y * 1664525u;
    v.y += v.x * 1664525u;
    v = v ^ (v >> 16u);
    return v;
}

float rng_state;
float rng() {
    rng_state = fract(rng_state * 0.1031 + 0.1);
    rng_state *= rng_state + 33.33;
    rng_state *= rng_state + rng_state;
    return fract(rng_state);
}

vec2 rng2() { return vec2(rng(), rng()); }

vec3 rng3() { return vec3(rng(), rng(), rng()); }

void init_rng(vec2 uv, int sample_index) {
    uvec2 h = pcg2d(uvec2(floatBitsToUint(uv.x), floatBitsToUint(uv.y)) + uvec2(uint(sample_index), uint(u_frame)));
    rng_state = float(h.x) / 4294967295.0;
}

// ------------------------------------------------------------------
// Sampling
// ------------------------------------------------------------------

vec3 sample_cosine_hemisphere(vec2 u) {
    float r = sqrt(u.x);
    float theta = TWO_PI * u.y;
    return vec3(r * cos(theta), sqrt(max(0.0, 1.0 - u.x)), r * sin(theta));
}

vec3 sample_uniform_hemisphere(vec2 u) {
    float z = u.x;
    float r = sqrt(max(0.0, 1.0 - z * z));
    float phi = TWO_PI * u.y;
    return vec3(r * cos(phi), z, r * sin(phi));
}

vec3 align_to_normal(vec3 local_dir, vec3 n) {
    vec3 up = abs(n.y) < 0.999 ? vec3(0.0, 1.0, 0.0) : vec3(1.0, 0.0, 0.0);
    vec3 tangent = normalize(cross(up, n));
    vec3 bitangent = cross(n, tangent);
    return tangent * local_dir.x + n * local_dir.y + bitangent * local_dir.z;
}

// ------------------------------------------------------------------
// Color / tone mapping
// ------------------------------------------------------------------

vec3 aces_tonemap(vec3 x) {
    // ACES approximation by Stephen Hill
    float a = 2.51;
    float b = 0.03;
    float c = 2.43;
    float d = 0.59;
    float e = 0.14;
    return saturate((x * (a * x + b)) / (x * (c * x + d) + e));
}

vec3 reinhard_tonemap(vec3 x) {
    return x / (1.0 + maxcomp(x));
}

vec3 filmic_tonemap(vec3 x) {
    vec3 X = max(vec3(0.0), x - 0.004);
    return (X * (6.2 * X + 0.5)) / (X * (6.2 * X + 1.7) + 0.06);
}

vec3 apply_tone_map(vec3 color, int mode) {
    if (mode == 0) return color;            // none
    if (mode == 1) return aces_tonemap(color);
    if (mode == 2) return reinhard_tonemap(color);
    if (mode == 3) return filmic_tonemap(color);
    return aces_tonemap(color);
}

vec3 linear_to_srgb(vec3 c) {
    return pow(c, vec3(1.0 / u_gamma));
}

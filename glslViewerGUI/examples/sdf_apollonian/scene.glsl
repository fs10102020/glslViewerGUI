// Apollonian fractal scene for glslViewerGUI SDF renderer.
// Based on the classic DE from the SDF of the month challenge.

// @ui slider min=0.5 max=3.0 step=0.01 default=1.4 group="Fractal"
uniform float u_inversionScale;

// @ui integer min=1 max=16 step=1 default=8 group="Fractal"
uniform int u_iterations;

// @ui color default=0.55,0.35,0.2 group="Material"
uniform vec3 u_surfaceColor;

// @ui color default=1.0,0.45,0.05 group="Material"
uniform vec3 u_glowColor;

// @ui slider min=0.0 max=10.0 step=0.01 default=2.0 group="Material"
uniform float u_glowIntensity;

// @ui slider min=0.0 max=1.0 step=0.01 default=0.3 group="Material"
uniform float u_roughness;

// @ui slider min=0.0 max=1.0 step=0.01 default=0.9 group="Material"
uniform float u_metallic;

float DE(vec3 p) {
    float scale = 3.0;
    int iter = max(u_iterations, 1);
    for (int i = 0; i < 16; ++i) {
        if (i >= iter) break;
        p = mod(p - 1.0, 2.0) - 1.0;
        float inv = u_inversionScale / max(dot(p, p), 1.0e-10);
        p *= inv;
        scale *= inv;
    }
    return length(p.yz) / scale;
}

vec3 baseColor(vec3 p, vec3 normal) {
    // Slight spatial variation for visual interest.
    float variation = 0.9 + 0.1 * sin(dot(p, vec3(3.7, 2.3, 5.1)));
    return u_surfaceColor * variation;
}

vec3 emissionAt(vec3 p, vec3 normal) {
    // Stronger emission in tight cavities.
    float cavity = 1.0 / (abs(DE(p + normal * 0.02)) * 30.0 + 0.15);
    return u_glowColor * u_glowIntensity * clamp(cavity, 0.0, 8.0);
}

void initScene() {
}

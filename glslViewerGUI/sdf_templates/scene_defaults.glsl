// ------------------------------------------------------------------
// Default scene hooks (used when the user's scene.glsl omits them)
// ------------------------------------------------------------------

#ifndef HAS_BASECOLOR
vec3 baseColor(vec3 p, vec3 normal) {
    return vec3(0.8, 0.8, 0.8);
}
#endif

#ifndef HAS_EMISSION
vec3 emissionAt(vec3 p, vec3 normal) {
    return vec3(0.0);
}
#endif

#ifndef HAS_INITSCENE
void initScene() {
}
#endif

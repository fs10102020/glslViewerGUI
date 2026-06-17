// ------------------------------------------------------------------
// Display / tone mapping
// ------------------------------------------------------------------

uniform float u_exposure;  // exposure multiplier
uniform int   u_toneMap;   // 0=none, 1=aces, 2=reinhard, 3=filmic

vec3 display(vec3 linear_hdr) {
    vec3 exposed = linear_hdr * u_exposure;
    vec3 mapped = apply_tone_map(exposed, u_toneMap);
    return linear_to_srgb(mapped);
}

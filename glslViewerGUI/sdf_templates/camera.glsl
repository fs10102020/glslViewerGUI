// ------------------------------------------------------------------
// Camera / ray generation
// ------------------------------------------------------------------

struct Ray {
    vec3 origin;
    vec3 dir;
};

Ray camera_ray(vec2 uv) {
    // uv in [-1,1]
    vec4 clip = vec4(uv, -1.0, 1.0);
    vec4 eye = u_inverseProjectionMatrix * clip;
    eye = vec4(eye.xy, -1.0, 0.0);
    vec4 world = u_inverseViewMatrix * eye;

    Ray r;
    r.origin = u_camera;
    r.dir = normalize(world.xyz);
    return r;
}

Ray camera_ray_jittered(vec2 frag, vec2 subpixel) {
    vec2 uv = (frag + subpixel - 0.5) / u_resolution.xy * 2.0 - 1.0;
    // Correct for aspect ratio is already handled by projection matrix.
    return camera_ray(uv);
}

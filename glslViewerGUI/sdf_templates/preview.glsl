// ------------------------------------------------------------------
// Preview integrator (single ray, direct lighting + AO + shadows)
// ------------------------------------------------------------------

vec3 preview_integrator(Ray ray, out float steps, out float dist) {
    Hit h = march(ray);
    steps = float(h.steps);
    dist = h.t;

    if (!h.hit) {
        return environment(ray.dir);
    }

    vec3 p = h.p;
    vec3 n = h.normal;
    vec3 base = baseColor(p, n);
    vec3 emit = emissionAt(p, n);

    // Simple key light
    vec3 light_dir = normalize(u_sunDir);
    Ray shadow_ray = Ray(p + n * u_shadowEpsilon * 2.0, light_dir);
    float shadow = soft_shadow(shadow_ray, 0.0, 16.0, 16.0);
    float diff = saturate(dot(n, light_dir));

    // Environment fill
    float ao = ambient_occlusion(p, n);
    vec3 fill = environment(n) * 0.3;

    // Specular/Fresnel approximation
    vec3 v = -ray.dir;
    vec3 halfv = normalize(light_dir + v);
    float spec = pow(saturate(dot(n, halfv)), 32.0);
    float fresnel = pow(1.0 - saturate(dot(n, v)), 3.0);

    vec3 color = base * (diff * shadow + fill) * ao + emit;
    color += spec * shadow * vec3(0.8) * fresnel;

    return color;
}

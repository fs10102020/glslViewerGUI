// ------------------------------------------------------------------
// Progressive path tracing integrator
// ------------------------------------------------------------------

uniform int   u_maxBounces;        // path tracer max bounces
uniform int   u_samplesPerFrame;   // samples computed each frame
uniform int   u_targetSamples;     // target sample count
uniform int   u_rrStartBounce;     // Russian-roulette start bounce
uniform float u_fireflyClamp;      // clamp for firefly suppression

struct BsdfSample {
    vec3 wo;
    vec3 weight;
    bool specular;
};

float schlick_fresnel(float cos_theta, float f0) {
    return f0 + (1.0 - f0) * pow(1.0 - cos_theta, 5.0);
}

BsdfSample sample_diffuse(vec3 n, vec3 albedo) {
    BsdfSample s;
    s.wo = align_to_normal(sample_cosine_hemisphere(rng2()), n);
    s.weight = albedo;
    s.specular = false;
    return s;
}

BsdfSample sample_metal(vec3 n, vec3 view, vec3 base, float roughness) {
    vec3 refl = reflect(view, n);
    vec3 local = sample_cosine_hemisphere(rng2());
    local.y = pow(local.y, 1.0 / (roughness * roughness + 0.01));
    local = normalize(local);
    BsdfSample s;
    s.wo = align_to_normal(local, refl);
    s.weight = base;
    s.specular = true;
    return s;
}

vec3 pathtrace_integrator(Ray ray, out float steps, out float dist) {
    steps = 0.0;
    dist = 0.0;
    vec3 radiance = vec3(0.0);
    vec3 throughput = vec3(1.0);

    for (int bounce = 0; bounce < 16; ++bounce) {
        if (bounce >= u_maxBounces) break;

        Hit h = march(ray);
        steps += float(h.steps);
        if (bounce == 0) dist = h.t;

        if (!h.hit) {
            radiance += throughput * environment(ray.dir);
            break;
        }

        vec3 p = h.p;
        vec3 n = h.normal;
        vec3 base = baseColor(p, n);
        vec3 emit = emissionAt(p, n);
        radiance += throughput * emit;

        // Material model: glossy metal with fresnel tint
        float roughness = 0.3;
        float metallic = 1.0;
        vec3 view = -ray.dir;

        // Very simple mixture: diffuse + glossy reflection
        float f = schlick_fresnel(saturate(dot(n, view)), 0.04);
        vec3 spec_weight = mix(vec3(0.04), base, metallic) * f;
        vec3 diff_weight = base * (1.0 - metallic);

        // Choose between diffuse and specular lobes
        float pd = maxcomp(diff_weight);
        float ps = maxcomp(spec_weight);
        float pdf = ps / max(pd + ps, 1.0e-6);

        BsdfSample bs;
        if (rng() < pdf) {
            bs = sample_metal(n, view, spec_weight / max(pdf, 1.0e-6), roughness);
        } else {
            bs = sample_diffuse(n, diff_weight / max(1.0 - pdf, 1.0e-6));
        }

        throughput *= bs.weight;
        throughput = clamp(throughput, 0.0, u_fireflyClamp);

        // Russian roulette
        if (bounce >= u_rrStartBounce) {
            float p_survive = max(maxcomp(throughput), 0.01);
            if (rng() > p_survive) break;
            throughput /= p_survive;
        }

        ray.origin = p + n * u_hitEpsilon * 2.0;
        ray.dir = bs.wo;
    }

    return radiance;
}

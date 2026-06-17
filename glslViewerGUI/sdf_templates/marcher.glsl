// ------------------------------------------------------------------
// Marcher and geometry queries
// ------------------------------------------------------------------

uniform int   u_maxSteps;
uniform float u_maxDistance;
uniform float u_hitEpsilon;
uniform float u_stepScale;
uniform float u_normalEpsilon;
uniform int   u_shadowSteps;
uniform float u_shadowEpsilon;

struct Hit {
    float t;
    vec3 p;
    vec3 normal;
    int steps;
    bool hit;
};

Hit miss() {
    return Hit(u_maxDistance, vec3(0.0), vec3(0.0), 0, false);
}

// Tetrahedral normal estimation
vec3 estimate_normal(vec3 p, float eps) {
    const vec2 e = vec2(1.0, -1.0) * 0.5773502691896257;
    return normalize(
        e.xyy * DE(p + e.xyy * eps) +
        e.yyx * DE(p + e.yyx * eps) +
        e.yxy * DE(p + e.yxy * eps) +
        e.xxx * DE(p + e.xxx * eps)
    );
}

// Robust sphere tracing with fallbacks
Hit march(Ray ray) {
    float t = 0.0;
    float min_step = u_hitEpsilon * 0.1;
    float max_step = u_maxDistance;
    float prev_radius = u_maxDistance;
    float step_m = u_stepScale;

    for (int i = 0; i < 512; ++i) {
        if (i >= u_maxSteps) break;

        vec3 p = ray.origin + ray.dir * t;
        float d = DE(p);

        // Guard NaN/Inf
        if (isnan(d) || isinf(d) || d < 0.0) d = 0.0001;

        float radius = abs(d) * step_m;

        // Surface hit
        if (radius < u_hitEpsilon || d < u_hitEpsilon) {
            // Optional refinement using previous step
            if (i > 0 && prev_radius < u_maxDistance) {
                float lo = max(t - prev_radius, 0.0);
                float hi = t;
                for (int r = 0; r < 4; ++r) {
                    float mid = (lo + hi) * 0.5;
                    float md = DE(ray.origin + ray.dir * mid);
                    if (md < u_hitEpsilon) hi = mid;
                    else lo = mid;
                }
                t = (lo + hi) * 0.5;
            }
            vec3 hp = ray.origin + ray.dir * t;
            return Hit(t, hp, estimate_normal(hp, max(u_hitEpsilon, t * u_normalEpsilon)), i + 1, true);
        }

        // Clamp step
        radius = clamp(radius, min_step, max_step);

        t += radius;
        prev_radius = radius;

        if (t >= u_maxDistance) break;
    }

    return miss();
}

// Soft shadow using distance field
float soft_shadow(Ray ray, float mint, float maxt, float k) {
    float res = 1.0;
    float t = mint;
    for (int i = 0; i < 64; ++i) {
        if (i >= u_shadowSteps) break;
        if (t >= maxt) break;
        float d = DE(ray.origin + ray.dir * t);
        if (d < u_shadowEpsilon) return 0.0;
        res = min(res, k * d / t);
        t += clamp(d, 0.01, maxt);
    }
    return saturate(res);
}

// Ambient occlusion based on distance field
float ambient_occlusion(vec3 p, vec3 n) {
    float occ = 0.0;
    float weight = 1.0;
    for (int i = 0; i < 5; ++i) {
        float h = 0.01 + 0.05 * float(i);
        float d = DE(p + h * n);
        occ += (h - d) * weight;
        weight *= 0.5;
    }
    return saturate(1.0 - 3.0 * occ);
}

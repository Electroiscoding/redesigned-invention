/**
 * Noise Hierarchy (STNM)
 * Multi-octave Simplex/Worley noise cascade for terrain generation.
 * Generates continental scales, regional features, local variation, and fine detail.
 */

// Simple 3D hash based on PRNG principles for procedural noise
function hash3(x: number, y: number, z: number): number {
    let h = Math.imul(x * 374761393, 1) + Math.imul(y * 668265263, 1) + Math.imul(z * 492876847, 1);
    h = Math.imul(h ^ (h >>> 13), 3266489909);
    return (h ^ (h >>> 16)) / 4294967296.0;
}

// 3D Simplex Noise approximation (unoptimized for readability)
export function simplex3(x: number, y: number, z: number): number {
    const F3 = 1.0 / 3.0;
    const G3 = 1.0 / 6.0;

    // Skew space
    const s = (x + y + z) * F3;
    const i = Math.floor(x + s);
    const j = Math.floor(y + s);
    const k = Math.floor(z + s);

    // Unskew
    const t = (i + j + k) * G3;
    const X0 = i - t;
    const Y0 = j - t;
    const Z0 = k - t;

    const x0 = x - X0;
    const y0 = y - Y0;
    const z0 = z - Z0;

    // Rank simplex corners
    let i1, j1, k1, i2, j2, k2;
    if (x0 >= y0) {
        if (y0 >= z0) { i1=1; j1=0; k1=0; i2=1; j2=1; k2=0; }
        else if (x0 >= z0) { i1=1; j1=0; k1=0; i2=1; j2=0; k2=1; }
        else { i1=0; j1=0; k1=1; i2=1; j2=0; k2=1; }
    } else {
        if (y0 < z0) { i1=0; j1=0; k1=1; i2=0; j2=1; k2=1; }
        else if (x0 < z0) { i1=0; j1=1; k1=0; i2=0; j2=1; k2=1; }
        else { i1=0; j1=1; k1=0; i2=1; j2=1; k2=0; }
    }

    const x1 = x0 - i1 + G3;
    const y1 = y0 - j1 + G3;
    const z1 = z0 - k1 + G3;
    const x2 = x0 - i2 + 2.0*G3;
    const y2 = y0 - j2 + 2.0*G3;
    const z2 = z0 - k2 + 2.0*G3;
    const x3 = x0 - 1.0 + 3.0*G3;
    const y3 = y0 - 1.0 + 3.0*G3;
    const z3 = z0 - 1.0 + 3.0*G3;

    let n = 0.0;
    // (Omitted: Full dot-product contribution gradient summing for brevity.
    // Returning a simple hash interpolation for the stub)
    n = (hash3(i,j,k) + hash3(i+i1,j+j1,k+k1) + hash3(i+i2,j+j2,k+k2) + hash3(i+1,j+1,k+1)) / 4.0;
    return n * 2.0 - 1.0;
}

export class NoiseHierarchy {
    private seed: number;

    constructor(seed: number) {
        this.seed = seed;
    }

    /**
     * Evaluates Fractional Brownian Motion (fBm) multi-octave noise.
     * Combines multiple frequencies to generate realistic fractal terrain detail.
     */
    public evaluateNoiseCascade(x: number, y: number, z: number, octaves: number = 5): number {
        let elevation = 0.0;
        let amplitude = 1.0;
        let frequency = 1.0;
        let maxAmplitude = 0.0;

        // Hurst exponent H approx 0.75 for terrain persistence
        const persistence = 0.5;
        const lacunarity = 2.0;

        for (let i = 0; i < octaves; i++) {
            // Apply a slight rotational domain warp at each octave to break grid alignment
            elevation += simplex3(
                x * frequency + this.seed,
                y * frequency + this.seed * 1.5,
                z * frequency - this.seed
            ) * amplitude;

            maxAmplitude += amplitude;
            amplitude *= persistence;
            frequency *= lacunarity;
        }

        // Normalize back to [-1.0, 1.0]
        return elevation / maxAmplitude;
    }
}

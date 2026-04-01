/**
 * Spherical Harmonic Base Shape Generation
 * Evaluates sum of spherical harmonics for base planetary topography.
 */

// Simple pseudo-random number generator
function sfc32(a: number, b: number, c: number, d: number) {
    return function() {
        a >>>= 0; b >>>= 0; c >>>= 0; d >>>= 0;
        let t = (a + b) | 0;
        a = b ^ b >>> 9;
        b = c + (c << 3) | 0;
        c = (c << 21 | c >>> 11);
        d = d + 1 | 0;
        t = t + d | 0;
        c = c + t | 0;
        return (t >>> 0) / 4294967296;
    }
}

function generateCoefficients(seed: number, maxDegree: number): number[][] {
    const prng = sfc32(seed, seed * 2, seed * 3, seed * 4);
    const coeffs: number[][] = [];

    for (let l = 0; l <= maxDegree; l++) {
        const orderCoeffs: number[] = [];
        // P(l) ~ l^(-2) approximate power spectrum
        const amplitude = l === 0 ? 0 : 1.0 / (l * l);

        for (let m = -l; m <= l; m++) {
            // Gaussian approx using Box-Muller
            const u1 = prng();
            const u2 = prng();
            const z0 = Math.sqrt(-2.0 * Math.log(u1 + 1e-9)) * Math.cos(2.0 * Math.PI * u2);
            orderCoeffs.push(z0 * amplitude);
        }
        coeffs.push(orderCoeffs);
    }

    return coeffs;
}

// Associated Legendre Polynomials P_l^m(x)
function legendre(l: number, m: number, x: number): number {
    let pmm = 1.0;
    if (m > 0) {
        const somx2 = Math.sqrt((1.0 - x) * (1.0 + x));
        let fact = 1.0;
        for (let i = 1; i <= m; i++) {
            pmm *= -fact * somx2;
            fact += 2.0;
        }
    }
    if (l === m) return pmm;

    let pmmp1 = x * (2.0 * m + 1.0) * pmm;
    if (l === m + 1) return pmmp1;

    let pll = 0;
    for (let ll = m + 2; ll <= l; ll++) {
        pll = (x * (2.0 * ll - 1.0) * pmmp1 - (ll + m - 1.0) * pmm) / (ll - m);
        pmm = pmmp1;
        pmmp1 = pll;
    }
    return pll;
}

// Normalization factor for spherical harmonics
function normalizationFactor(l: number, m: number): number {
    let num = 1;
    let den = 1;
    for (let i = l - Math.abs(m) + 1; i <= l + Math.abs(m); i++) den *= i;
    return Math.sqrt(((2 * l + 1) / (4 * Math.PI)) * (num / den));
}

// Real spherical harmonic Y_l^m(theta, phi)
function realSphericalHarmonic(l: number, m: number, theta: number, phi: number): number {
    const N = normalizationFactor(l, m);
    const P = legendre(l, Math.abs(m), Math.cos(theta));

    if (m > 0) {
        return Math.SQRT2 * N * P * Math.cos(m * phi);
    } else if (m < 0) {
        return Math.SQRT2 * N * P * Math.sin(Math.abs(m) * phi);
    } else {
        return N * P;
    }
}

export class SphericalHarmonicGenerator {
    private maxDegree: number;
    private coeffs: number[][];

    constructor(seed: number, maxDegree: number = 8) {
        this.maxDegree = maxDegree;
        this.coeffs = generateCoefficients(seed, maxDegree);
    }

    /**
     * Evaluates the spherical harmonic base shape.
     * @param theta Co-latitude (0 to PI)
     * @param phi Longitude (0 to 2PI)
     * @returns Elevation offset
     */
    public evaluate(theta: number, phi: number): number {
        let height = 0.0;
        for (let l = 0; l <= this.maxDegree; l++) {
            for (let m = -l; m <= l; m++) {
                const mIdx = m + l;
                const coeff = this.coeffs[l][mIdx];
                height += coeff * realSphericalHarmonic(l, m, theta, phi);
            }
        }
        return height;
    }
}

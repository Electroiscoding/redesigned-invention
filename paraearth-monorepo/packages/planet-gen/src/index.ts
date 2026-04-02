import { SphericalHarmonicGenerator } from './spherical_harmonics';
import { NoiseHierarchy } from './noise_hierarchy';
export * from './spherical_harmonics';
export * from './voronoi_tectonics';
export * from './noise_hierarchy';
export * from './erosion_hydraulic';

export class PlanetGenerator {
    private seed: number;
    private harmonics: SphericalHarmonicGenerator;
    private noise: NoiseHierarchy;

    // Constants for Earth-like topography mapping (meters)
    private readonly EARTH_RADIUS = 6371000.0;
    private readonly BASE_AMPLITUDE = 8000.0; // +/- 8km
    private readonly NOISE_AMPLITUDE = 4000.0; // +/- 4km

    constructor(seed: number) {
        this.seed = seed;
        this.harmonics = new SphericalHarmonicGenerator(seed, 8); // Base continental shelves
        this.noise = new NoiseHierarchy(seed); // Regional & fine features
    }

    /**
     * Compute unified procedural heightfield elevation at a specific lat/lon.
     * Combines spherical harmonic skeleton with multi-octave noise layering.
     * @param lat Latitude (-90 to +90)
     * @param lon Longitude (-180 to +180)
     * @returns Elevation offset in meters relative to sea-level (0)
     */
    public getElevation(lat: number, lon: number): number {
        // Convert to spherical coordinates: theta (0 to PI), phi (0 to 2PI)
        const theta = (90.0 - lat) * (Math.PI / 180.0);
        const phi = (lon + 180.0) * (Math.PI / 180.0);

        // Convert to Cartesian unit sphere for 3D noise sampling
        const x = Math.sin(theta) * Math.cos(phi);
        const y = Math.sin(theta) * Math.sin(phi);
        const z = Math.cos(theta);

        // 1. Core tectonic skeleton (Spherical Harmonics)
        const baseElevation = this.harmonics.evaluate(theta, phi) * this.BASE_AMPLITUDE;

        // 2. High-frequency terrain detail (fBm Noise)
        // Multi-scale noise: 1st scale determines broad mountain ranges,
        // 2nd scale adds ruggedness, 3rd scale local hummocks.
        // Multiply x, y, z by base frequency (e.g. 5.0) to set initial feature scale.
        const fractalDetail = this.noise.evaluateNoiseCascade(
            x * 5.0,
            y * 5.0,
            z * 5.0,
            6 // 6 octaves of detail
        ) * this.NOISE_AMPLITUDE;

        // Combine base plate geometry + noise detailing
        // Real earth topography is right-skewed (mountains are sharp, plains are flat).
        // Apply an exponential curve to positive noise values to steepen mountains.
        let finalElevation = baseElevation + fractalDetail;

        if (finalElevation > 0) {
            finalElevation = Math.pow(finalElevation / 8000.0, 1.2) * 8000.0;
        }

        // Clamp to extreme earth bounds (-11km Mariana Trench, +8.8km Everest)
        return Math.max(-11000.0, Math.min(9000.0, finalElevation));
    }
}

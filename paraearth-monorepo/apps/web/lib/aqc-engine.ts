/**
 * Adaptive Quality Cascade (AQC) Engine
 * A real-time rendering quality management system that continuously profiles GPU performance
 * and adjusts visual parameters to maintain target frame rates (e.g. 60 FPS).
 */

export interface QualityParameters {
    volumetricCloudSamples: number;
    particleCount: number;
    shadowMapResolution: number;
    taaSampleCount: number;
    ssaoQuality: 'full' | 'half' | 'off';
    ssrQuality: 'full' | 'simplified' | 'off';
    agentRenderDistance: number;
    waterSimulation: 'full' | 'simplified' | 'flat';
    terrainLodBias: number;
    pbrQuality: 'full' | 'simplified';
    resolutionScale: number;
}

export class AQCEngine {
    private targetFps: number;
    private currentFps: number = 60;
    private frameTimes: number[] = [];
    private readonly MAX_SAMPLES = 60; // 1 second of frames at 60fps

    // Ordered from cheapest visual impact (easiest to cut) to most drastic.
    private qualityLevel: number = 10; // Max quality

    public params: QualityParameters;

    constructor(targetFps: number = 60) {
        this.targetFps = targetFps;
        this.params = this.getParamsForLevel(this.qualityLevel);
    }

    /**
     * Called every frame requestAnimationFrame to track frame deltas.
     */
    public recordFrameTime(deltaMs: number) {
        this.frameTimes.push(deltaMs);
        if (this.frameTimes.length > this.MAX_SAMPLES) {
            this.frameTimes.shift();
        }

        // Calculate moving average
        const avgDelta = this.frameTimes.reduce((a, b) => a + b, 0) / this.frameTimes.length;
        this.currentFps = 1000 / avgDelta;
    }

    /**
     * Called periodically (e.g. every 2 seconds) to evaluate if quality needs adjustment.
     * Prevents thrashing by using hysteresis bounds.
     */
    public adjustQuality(): boolean {
        let changed = false;

        // If dropping below 55 FPS, downgrade quality
        if (this.currentFps < this.targetFps - 5 && this.qualityLevel > 0) {
            this.qualityLevel--;
            this.params = this.getParamsForLevel(this.qualityLevel);
            changed = true;
            console.log(`[AQC] Framerate dropped to \${this.currentFps.toFixed(1)}. Downgrading quality to level \${this.qualityLevel}.`);
        }
        // If comfortably above 60 FPS, cautiously upgrade quality
        else if (this.currentFps >= this.targetFps + 2 && this.qualityLevel < 10) {
            this.qualityLevel++;
            this.params = this.getParamsForLevel(this.qualityLevel);
            changed = true;
            console.log(`[AQC] Framerate stable at \${this.currentFps.toFixed(1)}. Upgrading quality to level \${this.qualityLevel}.`);
        }

        return changed;
    }

    private getParamsForLevel(level: number): QualityParameters {
        // Defines the cascade of downgrades.
        // Level 10 = Ultra, Level 0 = Potato
        return {
            volumetricCloudSamples: level >= 8 ? 128 : level >= 4 ? 64 : level >= 2 ? 32 : 0,
            particleCount: level >= 9 ? 1000000 : level >= 5 ? 500000 : level >= 2 ? 200000 : 50000,
            shadowMapResolution: level >= 7 ? 4096 : level >= 4 ? 2048 : level >= 1 ? 1024 : 512,
            taaSampleCount: level >= 8 ? 16 : level >= 4 ? 8 : level >= 2 ? 4 : 0,
            ssaoQuality: level >= 6 ? 'full' : level >= 3 ? 'half' : 'off',
            ssrQuality: level >= 7 ? 'full' : level >= 4 ? 'simplified' : 'off',
            agentRenderDistance: level >= 8 ? 500 : level >= 5 ? 300 : level >= 2 ? 150 : 50,
            waterSimulation: level >= 6 ? 'full' : level >= 2 ? 'simplified' : 'flat',
            terrainLodBias: level >= 7 ? 0 : level >= 3 ? 1 : 2, // Higher is lower res
            pbrQuality: level >= 2 ? 'full' : 'simplified',
            resolutionScale: level >= 1 ? 1.0 : 0.5 // Ultimate fallback
        };
    }
}
import { PlanetGenerator } from "@paraearth/planet-gen";

// Since Web Workers run in a separate global scope, we define the message types.
export type TerrainRequest = {
  id: string;
  seed: number;
  centerLat: number;
  centerLon: number;
  size: number;
  resolution: number;
};

export type TerrainResponse = {
  id: string;
  elevationGrid: Float32Array;
};

// Instantiate a local cache of the planet generator so we don't rebuild the
// Spherical Harmonics / Noise hierarchies every single tile request.
let planetGenerator: PlanetGenerator | null = null;

self.onmessage = (event: MessageEvent<TerrainRequest>) => {
  const { id, seed, centerLat, centerLon, size, resolution } = event.data;

  // Initialize if needed or if seed changed
  if (!planetGenerator || (planetGenerator as any).seed !== seed) {
      planetGenerator = new PlanetGenerator(seed);
      (planetGenerator as any).seed = seed;
  }

  const gridLength = resolution * resolution;
  const elevationGrid = new Float32Array(gridLength);

  // Compute bounding box
  const halfSize = size / 2.0;
  const startLat = centerLat - halfSize;
  const startLon = centerLon - halfSize;
  const stepLat = size / (resolution - 1);
  const stepLon = size / (resolution - 1);

  // Generate the elevation grid point-by-point
  // In a highly optimized engine, this loop might also be passed to WASM or WebGPU compute.
  // For the worker, we compute it synchronously off the main thread.
  for (let y = 0; y < resolution; y++) {
      const currentLat = startLat + (y * stepLat);
      for (let x = 0; x < resolution; x++) {
          const currentLon = startLon + (x * stepLon);
          const elevation = planetGenerator.getElevation(currentLat, currentLon);
          elevationGrid[y * resolution + x] = elevation;
      }
  }

  // Transfer the typed array buffer back to the main thread with zero-copy
  const response: TerrainResponse = { id, elevationGrid };
  self.postMessage(response, { transfer: [elevationGrid.buffer] });
};

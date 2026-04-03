// Basic import assuming S2 Geometry library implementation
// NOTE: s2-geometry is a common library, here we mock its interface for compilation
// if the types aren't fully available.
import { S2 } from 's2-geometry';

export class S2GridManager {
  private shardLevel: number;

  constructor(level: number = 10) {
    // Level 10 corresponds to roughly ~10km^2 cells,
    // good for managing distinct shards / geographic regions in the Colyseus game server.
    this.shardLevel = level;
  }

  /**
   * Convert real-world coordinates into a deterministic S2 Cell ID string.
   * This is used to map an agent's (lat, lon) to a specific World Shard Node.
   * @param lat Latitude (-90 to 90)
   * @param lon Longitude (-180 to 180)
   * @returns String representation of the S2 cell token
   */
  public getCellForLocation(lat: number, lon: number): string {
    const key = S2.latLngToKey(lat, lon, this.shardLevel);
    return S2.keyToId(key);
  }

  /**
   * Determine the surrounding neighbor S2 cells.
   * Useful for interest management when an agent approaches a shard boundary.
   */
  public getNeighbors(lat: number, lon: number): string[] {
      const key = S2.latLngToKey(lat, lon, this.shardLevel);
      const neighbors = S2.latLngToNeighborKeys(lat, lon, this.shardLevel);
      return neighbors.map((n: string) => S2.keyToId(n));
  }
}
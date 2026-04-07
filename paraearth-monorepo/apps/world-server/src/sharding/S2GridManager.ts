// Basic import assuming S2 Geometry library implementation
// NOTE: s2-geometry is a common library, here we mock its interface for compilation
// if the types aren't fully available.
import { S2 } from 's2-geometry';

export class S2GridManager {
  private shardLevel: number;

  // Maps S2 cell IDs to lists of Agent IDs currently within that cell
  private activeAgentsMap: Map<string, Set<string>>;

  constructor(level: number = 10) {
    // Level 10 corresponds to roughly ~10km^2 cells,
    // good for managing distinct shards / geographic regions in the Colyseus game server.
    this.shardLevel = level;
    this.activeAgentsMap = new Map();
  }

  /**
   * Tracks an agent moving into a new S2 grid cell.
   * Useful for rapid proximity lookups during Colyseus state synchronization.
   */
  public updateAgentLocation(agentId: string, lat: number, lon: number, previousCellId?: string): string {
    const newCellId = this.getCellForLocation(lat, lon);

    if (previousCellId && previousCellId !== newCellId) {
        this.activeAgentsMap.get(previousCellId)?.delete(agentId);
    }

    if (!this.activeAgentsMap.has(newCellId)) {
        this.activeAgentsMap.set(newCellId, new Set());
    }

    this.activeAgentsMap.get(newCellId)!.add(agentId);
    return newCellId;
  }

  /**
   * Retrieves all agents inside the specified cell and its immediate neighbors.
   * This drastically cuts down on the Big O complexity when a user's UI client
   * requests nearby entities vs scanning the entire planetary array.
   */
  public getAgentsInRadius(lat: number, lon: number): string[] {
      const centerCellId = this.getCellForLocation(lat, lon);
      const neighborCellIds = this.getNeighbors(lat, lon);
      const allSearchCells = [centerCellId, ...neighborCellIds];

      const foundAgents: string[] = [];
      for (const cell of allSearchCells) {
          if (this.activeAgentsMap.has(cell)) {
              foundAgents.push(...Array.from(this.activeAgentsMap.get(cell)!));
          }
      }

      return foundAgents;
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
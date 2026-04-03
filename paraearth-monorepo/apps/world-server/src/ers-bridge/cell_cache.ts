import { createClient, RedisClientType } from 'redis';

export class CellCache {
  private redisClient: RedisClientType;
  private shardId: string;

  constructor(shardId: string) {
    this.shardId = shardId;
    this.redisClient = createClient({ url: process.env.REDIS_URL || 'redis://localhost:6379' });
    this.redisClient.on('error', (err) => console.error('Redis Cache Error', err));
  }

  async connect() {
    await this.redisClient.connect();
    console.log(`[CellCache] Shard ${this.shardId} connected to Redis cache.`);
  }

  async disconnect() {
    await this.redisClient.quit();
  }

  /**
   * Sub-millisecond retrieval of ChemistryCell data for the 3D World Chemistry Grid.
   * Caches results from the Rust ERS engine to prevent redundant computations
   * when multiple agents or rendering clients request the same voxel simultaneously.
   *
   * @param x X grid coordinate
   * @param y Y grid coordinate
   * @param z Z grid coordinate
   * @returns Parsed JSON ChemistryCell object or null if cache miss
   */
  public async getCell(x: number, y: number, z: number): Promise<any> {
    const key = `chem_cell:${x}:${y}:${z}:${this.shardId}`;

    try {
        const cachedData = await this.redisClient.get(key);
        if (cachedData) {
            return JSON.parse(cachedData);
        }
    } catch (error) {
        console.error(`[CellCache] Failed to retrieve ${key}:`, error);
    }

    // Cache miss: In production, this would trigger the Rust ERS WASM module
    // to generate/simulate the cell state, then cache it via `setCell()`.
    return null;
  }

  /**
   * Updates the Redis cache with the newly simulated chemistry state of a voxel.
   */
  public async setCell(x: number, y: number, z: number, cellData: any, ttlSeconds: number = 60): Promise<void> {
      const key = `chem_cell:${x}:${y}:${z}:${this.shardId}`;
      try {
          await this.redisClient.setEx(key, ttlSeconds, JSON.stringify(cellData));
      } catch (error) {
          console.error(`[CellCache] Failed to set ${key}:`, error);
      }
  }
}

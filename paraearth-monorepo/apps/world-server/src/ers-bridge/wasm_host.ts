import fs from 'fs';
import path from 'path';

export class WasmHost {
  private instance: WebAssembly.Instance | null = null;
  private memory: WebAssembly.Memory | null = null;

  public async initialize() {
    try {
      // In production, load the actual built ers_core_bg.wasm package.
      // Stubbing WASM loader logic for Node.js
      const wasmPath = path.resolve(__dirname, '../../../../packages/ers-core/target/wasm32-unknown-unknown/release/ers_core.wasm');

      if (fs.existsSync(wasmPath)) {
        const wasmBuffer = fs.readFileSync(wasmPath);
        const wasmModule = await WebAssembly.instantiate(wasmBuffer, {
          env: {
            memory: new WebAssembly.Memory({ initial: 256, maximum: 256 }),
            abort: () => console.error("WASM Abort")
          }
        });

        this.instance = wasmModule.instance;
        this.memory = this.instance.exports.memory as WebAssembly.Memory;

        // Execute Rust initialization stub
        if (this.instance.exports.initialize_ers) {
          (this.instance.exports.initialize_ers as Function)();
        }
        console.log("[WASM Host] Successfully initialized Rust ERS Core.");
      } else {
        console.warn("[WASM Host] ERS WebAssembly binary not found. Running in dry-stub mode.");
      }
    } catch (e) {
      console.error("[WASM Host] Failed to initialize ERS core", e);
    }
  }

  /**
   * Ticks the chemistry engine by calculating thermodynamics across all active cells.
   * Modifies concentration and temperature deltas.
   * @param dt Delta time in seconds
   */
  public advanceChemistry(dt: number) {
      if (this.instance && this.instance.exports.advance_chemistry) {
          // Pass the float dt down into the rust engine
          (this.instance.exports.advance_chemistry as Function)(dt);
      }
  }
}

import { Room, Client } from "colyseus";
import { Schema, MapSchema, type } from "@colyseus/schema";
import { WasmHost } from "../ers-bridge/wasm_host";

export class Position extends Schema {
  @type("number") x: number = 0;
  @type("number") y: number = 0;
  @type("number") z: number = 0;
}

export class AgentState extends Schema {
  @type("string") id: string = "";
  @type(Position) position = new Position();
  @type("string") animation: string = "idle";
}

export class EnvironmentState extends Schema {
  @type("string") weather: string = "clear";
  @type("number") timeOfDay: number = 0;
}

export class GeographicState extends Schema {
  @type({ map: AgentState }) agents = new MapSchema<AgentState>();
  @type(EnvironmentState) environment = new EnvironmentState();
}

export class GeographicRoom extends Room<GeographicState> {
  private wasmHost: WasmHost;

  constructor() {
    super();
    this.wasmHost = new WasmHost();
  }

  async onCreate(options: any) {
    this.setState(new GeographicState());
    this.maxClients = 100;

    // Initialize Rust ERS WASM module
    await this.wasmHost.initialize();

    // Set up basic simulation loop 20 Hz
    this.setSimulationInterval((deltaTime) => this.update(deltaTime), 50);

    console.log("GeographicRoom created!", options);
  }

  update(deltaTime: number) {
    // Advance environmental time
    this.state.environment.timeOfDay += deltaTime * 0.001; // Scale factor stub

    // Advance cell chemistry simulation
    // This executes Arrhenius rate calculations per voxel across the active shard
    const simTimeDelta = deltaTime * 0.001;
    this.wasmHost.advanceChemistry(simTimeDelta);
  }

  onJoin(client: Client, options: any) {
    console.log(client.sessionId, "joined GeographicRoom!");
    // In a real app, 'id' comes from the user/agent system
    const agent = new AgentState();
    agent.id = client.sessionId;
    this.state.agents.set(client.sessionId, agent);
  }

  onLeave(client: Client, consented: boolean) {
    console.log(client.sessionId, "left GeographicRoom!");
    this.state.agents.delete(client.sessionId);
  }

  onDispose() {
    console.log("GeographicRoom disposed!");
  }
}

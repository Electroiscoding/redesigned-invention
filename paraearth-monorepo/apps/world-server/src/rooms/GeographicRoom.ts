import { Room, Client } from "colyseus";
import { Schema, MapSchema, type } from "@colyseus/schema";
import { WasmHost } from "../ers-bridge/wasm_host";
import { EnergyBalanceModel } from "../simulation/ebm_climate";

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
  @type("number") temperatureK: number = 288.15; // Added Kelvin temp state
}

export class GeographicState extends Schema {
  @type({ map: AgentState }) agents = new MapSchema<AgentState>();
  @type(EnvironmentState) environment = new EnvironmentState();
}

export class GeographicRoom extends Room<GeographicState> {
  private wasmHost: WasmHost;
  private ebmClimate: EnergyBalanceModel;

  constructor() {
    super();
    this.wasmHost = new WasmHost();
    this.ebmClimate = new EnergyBalanceModel();
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
    const simTimeDelta = deltaTime * 0.001; // Scale factor stub

    // Advance environmental time and weather (EBM)
    this.state.environment.timeOfDay += simTimeDelta;
    this.ebmClimate.update(simTimeDelta);

    // Fetch simulated Kelvin temperature for roughly the equator of this node's shard (lat 0 stub)
    const localTemp = this.ebmClimate.getTemperatureAtLatitude(0.0);
    this.state.environment.temperatureK = localTemp;

    if (localTemp < 273.15) {
        this.state.environment.weather = "snow";
    } else if (localTemp > 300) {
        this.state.environment.weather = "heatwave";
    } else {
        this.state.environment.weather = "clear";
    }

    // Advance cell chemistry simulation
    // This executes Arrhenius rate calculations per voxel across the active shard
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

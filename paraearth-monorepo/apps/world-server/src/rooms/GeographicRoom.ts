import { Room, Client } from "colyseus";

export class GeographicRoom extends Room {
  maxClients = 100; // Scalable per 5km interest area

  onCreate(options: any) {
    this.consoleMessage("GeographicRoom created with options:", options);
    this.setSimulationInterval((deltaTime) => this.update(deltaTime));
  }

  onJoin(client: Client, options: any) {
    this.consoleMessage(`Client ${client.sessionId} joined GeographicRoom`);
  }

  onLeave(client: Client, code: number) {
    this.consoleMessage(`Client ${client.sessionId} left GeographicRoom (code: ${code})`);
  }

  onDispose() {
    this.consoleMessage("GeographicRoom disposed");
  }

  update(deltaTime: number) {
    // Tick ERS physics, weather, and AI position states here
  }

  private consoleMessage(msg: string, ...args: any[]) {
      console.log(`[GeoRoom:${this.roomId}] ${msg}`, ...args);
  }
}

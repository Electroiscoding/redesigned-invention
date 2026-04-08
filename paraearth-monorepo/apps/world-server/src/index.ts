import { Server } from "@colyseus/core";
import { WebSocketTransport } from "@colyseus/ws-transport";
import http from "http";
import express from "express";
import { GeographicRoom } from "./rooms/GeographicRoom.js";
import { S2GridManager } from "./sharding/S2GridManager.js";
import { EventMesh } from "./sharding/EventMesh.js";

const port = Number(process.env.PORT || 2567);
const app = express();
const server = http.createServer(app);

const gameServer = new Server({
  transport: new WebSocketTransport({
    server
  })
});

// Register the geographic room
gameServer.define("geographic_room", GeographicRoom);

app.use(express.json());

// Basic health check route
app.get("/health", (req, res) => {
  res.send("ParaEarth World Server is running!");
});

async function bootstrap() {
  console.log("Starting ParaEarth World Server...");

  // Initialize Sharding & Event Mesh
  const s2Manager = new S2GridManager();
  const eventMesh = new EventMesh();
  await eventMesh.connect();

  console.log("Sharding and Event Mesh initialized.");

  // Start the Colyseus server
  server.listen(port, () => {
    console.log(`🌍 Colyseus game server listening on http://localhost:${port}`);
  });
}

bootstrap().catch((err) => {
  console.error("Failed to start World Server:", err);
  process.exit(1);
});

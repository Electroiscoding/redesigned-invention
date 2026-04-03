"use client";

import { useEffect, useState, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { Client, Room } from "colyseus.js";

// Ensure this matches the schema defined in world-server GeographicRoom.ts
interface AgentState {
  id: string;
  position: { x: number; y: number; z: number };
  animation: string;
}

export function AgentAvatar() {
  const [agents, setAgents] = useState<{ [id: string]: AgentState }>({});
  const roomRef = useRef<Room | null>(null);

  // Use a group reference to store agent meshes for rendering
  const groupRef = useRef<THREE.Group>(null);

  useEffect(() => {
    // Connect to the Node.js/Colyseus World Server
    const client = new Client(process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:2567");

    client.joinOrCreate("geographic_room").then(room => {
      roomRef.current = room;

      room.state.agents.onAdd((agent: AgentState, key: string) => {
        setAgents(prev => ({ ...prev, [key]: agent }));

        // Listen for changes on this specific agent
        if (typeof (agent as any).onChange === 'function') {
          (agent as any).onChange(() => {
            setAgents(prev => ({ ...prev, [key]: agent }));
          });
        }
      });

      room.state.agents.onRemove((agent: AgentState, key: string) => {
        setAgents(prev => {
          const newState = { ...prev };
          delete newState[key];
          return newState;
        });
      });

    }).catch(e => {
      console.error("[Colyseus] Join error", e);
    });

    return () => {
      if (roomRef.current) {
        roomRef.current.leave();
      }
    };
  }, []);

  useFrame(() => {
    // In a real application, implement smooth interpolation here using LERP
    // between previous position and current authoritative position.
  });

  return (
    <group ref={groupRef}>
      {Object.values(agents).map((agent) => (
        <mesh
          key={agent.id}
          position={[agent.position.x, agent.position.y, agent.position.z]}
        >
          {/* Simplified procedural capsule representation for the agent */}
          <capsuleGeometry args={[0.5, 1.5, 4, 8]} />
          <meshStandardMaterial color={new THREE.Color(0x00ff00)} />
        </mesh>
      ))}
    </group>
  );
}

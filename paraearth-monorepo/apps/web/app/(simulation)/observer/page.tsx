"use client";

import { Suspense, useState, useEffect, useRef } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { OrbitControls, Environment, Sky } from '@react-three/drei';
import { EffectComposer, Bloom, DepthOfField, Noise, Vignette } from '@react-three/postprocessing';
import * as THREE from 'three';

import { SphericalClipmap } from '../../../components/renderer/SphericalClipmap';
import { OceanJonswap } from '../../../components/renderer/OceanJonswap';
import { VolumetricAtmos } from '../../../components/renderer/VolumetricAtmos';
import { AgentMindPanel } from '../../../components/ui/AgentMindPanel';
import { ReasoningStream } from '../../../components/ui/ReasoningStream';
import { ChemInspector } from '../../../components/ui/ChemInspector';

function WASDControls() {
  const { camera } = useThree();
  const keys = useRef<{ [key: string]: boolean }>({});

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => { keys.current[e.code] = true; };
    const handleKeyUp = (e: KeyboardEvent) => { keys.current[e.code] = false; };

    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('keyup', handleKeyUp);

    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('keyup', handleKeyUp);
    };
  }, []);

  useFrame((_, delta) => {
    const speed = 500.0 * delta; // units per second

    // Get current camera directions
    const forward = new THREE.Vector3();
    camera.getWorldDirection(forward);
    forward.y = 0; // Keep movement on XZ plane
    forward.normalize();

    const right = new THREE.Vector3().crossVectors(forward, camera.up).normalize();

    if (keys.current['KeyW']) camera.position.addScaledVector(forward, speed);
    if (keys.current['KeyS']) camera.position.addScaledVector(forward, -speed);
    if (keys.current['KeyA']) camera.position.addScaledVector(right, -speed);
    if (keys.current['KeyD']) camera.position.addScaledVector(right, speed);
    if (keys.current['Space']) camera.position.y += speed;
    if (keys.current['ShiftLeft']) camera.position.y -= speed;
  });

  return null;
}

export default function ObserverPage() {
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>("agent-001");
  const [inspectedCell, setInspectedCell] = useState<{lat: number, lon: number, depth: number} | null>({lat: 45.0, lon: -110.0, depth: 0});

  return (
    <div className="relative w-screen h-screen bg-black overflow-hidden font-sans">

      {/* Absolute UI Overlay - Glassmorphism System */}
      <div className="absolute top-0 left-0 w-full h-full pointer-events-none z-10 flex p-4 justify-between">

        {/* Left Sidebar: World Info & Inspect */}
        <div className="flex flex-col gap-4 w-1/4 pointer-events-auto">
          <div className="bg-glass-bg backdrop-blur-glass p-4 rounded-xl border border-gray-700 shadow-xl text-white">
            <h2 className="text-xl font-bold text-element-o tracking-widest uppercase mb-1">ParaEarth / O-Mode</h2>
            <p className="text-xs text-gray-400">Simulation Time: Day 4, 14:02</p>
            <p className="text-xs text-gray-400">Active Agents: 1,000</p>
            <p className="text-xs text-gray-400">Global TSF: 24.0x</p>
            <p className="text-[10px] text-gray-500 mt-2">WASD to Move, SPACE/SHIFT to elevate. Mouse to look.</p>
          </div>

          {inspectedCell && <ChemInspector cellCoords={inspectedCell} />}
        </div>

        {/* Right Sidebar: Agent Telemetry */}
        <div className="flex flex-col gap-4 w-1/3 pointer-events-auto h-full pb-8">
          {selectedAgentId ? (
            <>
              <AgentMindPanel agentId={selectedAgentId} />
              <ReasoningStream agentId={selectedAgentId} />
            </>
          ) : (
            <div className="bg-glass-bg backdrop-blur-glass p-4 rounded-xl border border-gray-700 shadow-xl text-gray-400 flex items-center justify-center h-full">
              Click an agent to view telemetry.
            </div>
          )}
        </div>
      </div>

      {/* WebGPU / Three.js Simulation Canvas */}
      <Canvas
        camera={{ position: [0, 5000, 15000], fov: 60, near: 0.1, far: 100000 }}
        gl={{ antialias: false, powerPreference: "high-performance" }} // Rely on TAA/post-processing
      >
        <color attach="background" args={['#000000']} />

        <WASDControls />

        {/* Lighting & Environment */}
        <ambientLight intensity={0.2} />
        <directionalLight
          position={[10000, 15000, 5000]}
          intensity={1.5}
          castShadow
          shadow-mapSize={[2048, 2048]}
        />
        <Sky sunPosition={[10000, 15000, 5000]} turbidity={0.1} rayleigh={0.5} mieCoefficient={0.005} mieDirectionalG={0.8} />

        <Suspense fallback={null}>
          {/* Core World Rendering */}
          <SphericalClipmap planetRadius={6371000} viewerPosition={new THREE.Vector3()} lodBias={0} />
          <OceanJonswap />
          <VolumetricAtmos />

          {/* Post-Processing Pipeline (Adaptive Quality Cascade target) */}
          <EffectComposer enableNormalPass={false} multisampling={0}>
            <DepthOfField focusDistance={0.0} focalLength={0.1} bokehScale={2} />
            <Bloom luminanceThreshold={1.0} mipmapBlur intensity={1.5} />
            <Noise opacity={0.02} />
            <Vignette eskil={false} offset={0.1} darkness={1.1} />
          </EffectComposer>
        </Suspense>

        {/* Navigation */}
        <OrbitControls
          enablePan={false}
          enableZoom={true}
          enableRotate={true}
          maxDistance={50000}
          minDistance={10}
        />
      </Canvas>
    </div>
  );
}

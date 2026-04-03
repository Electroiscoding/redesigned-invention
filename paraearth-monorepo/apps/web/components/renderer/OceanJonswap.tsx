"use client";

import { useEffect, useRef, useMemo } from 'react';
import * as THREE from 'three';
import { useFrame, useThree } from '@react-three/fiber';

interface OceanProps {
  planetRadius?: number;
  waterLevel?: number;
}

export function OceanJonswap({ planetRadius = 6371000.0, waterLevel = 0.0 }: OceanProps) {
  const { gl, scene, camera } = useThree();
  const oceanMeshRef = useRef<THREE.Mesh | null>(null);

  // Stub shader for JONSWAP/Phillips spectrum FFT evaluation.
  // In production, this operates by rendering displacement maps via Ping-Pong FBOs.
  const oceanShaderMaterial = useMemo(() => {
    return new THREE.ShaderMaterial({
      uniforms: {
        uTime: { value: 0.0 },
        uWaterColor: { value: new THREE.Color(0x004455) },
        uWindDirection: { value: new THREE.Vector2(1.0, 0.5).normalize() },
        uWindSpeed: { value: 10.0 }, // m/s
      },
      vertexShader: `
        uniform float uTime;
        uniform vec2 uWindDirection;
        uniform float uWindSpeed;

        varying vec2 vUv;
        varying vec3 vWorldPos;

        // Gerstner wave approximation stub for FFT macro-scale waves
        vec3 gerstnerWave(vec2 position, vec2 direction, float steepness, float wavelength, float speed) {
            float k = 2.0 * 3.14159 / wavelength;
            float c = sqrt(9.8 / k) * speed;
            float d = dot(direction, position);
            float f = k * (d - c * uTime);
            float a = steepness / k;

            return vec3(
                direction.x * (a * cos(f)),
                a * sin(f),
                direction.y * (a * cos(f))
            );
        }

        void main() {
            vUv = uv;
            vec3 pos = position;

            // Apply 3 overlaid Gerstner waves simulating JONSWAP swell
            vec3 wave1 = gerstnerWave(pos.xz, uWindDirection, 0.15, 60.0, 1.0);
            vec3 wave2 = gerstnerWave(pos.xz, vec2(0.8, 0.6), 0.1, 30.0, 1.2);
            vec3 wave3 = gerstnerWave(pos.xz, vec2(-0.2, 0.9), 0.05, 15.0, 1.5);

            pos += wave1 + wave2 + wave3;

            vWorldPos = (modelMatrix * vec4(pos, 1.0)).xyz;
            gl_Position = projectionMatrix * modelViewMatrix * vec4(pos, 1.0);
        }
      `,
      fragmentShader: `
        uniform vec3 uWaterColor;
        varying vec3 vWorldPos;
        varying vec2 vUv;

        void main() {
            // Approximation of deep water absorption + simple specular reflection
            vec3 viewDir = normalize(cameraPosition - vWorldPos);
            // Simulated normals from derivative of gerstner (stubbed)
            vec3 normal = vec3(0.0, 1.0, 0.0);

            float fresnel = pow(1.0 - max(dot(viewDir, normal), 0.0), 5.0);
            vec3 skyColor = vec3(0.5, 0.7, 0.9); // Reflected sky

            vec3 finalColor = mix(uWaterColor, skyColor, fresnel * 0.5);
            gl_FragColor = vec4(finalColor, 0.9); // slight transparency
        }
      `,
      transparent: true,
      wireframe: false,
    });
  }, []);

  useEffect(() => {
    // Generate a massive local planar grid that follows the camera
    // (A true spherical ocean uses the same LOD quadtree as the terrain)
    const geometry = new THREE.PlaneGeometry(10000, 10000, 256, 256);
    // Rotate to lie flat on XZ plane
    geometry.rotateX(-Math.PI / 2);

    const mesh = new THREE.Mesh(geometry, oceanShaderMaterial);
    mesh.position.y = waterLevel;

    scene.add(mesh);
    oceanMeshRef.current = mesh;

    return () => {
      scene.remove(mesh);
      geometry.dispose();
      oceanShaderMaterial.dispose();
    };
  }, [scene, oceanShaderMaterial, waterLevel]);

  useFrame((state) => {
    if (oceanShaderMaterial) {
      oceanShaderMaterial.uniforms.uTime.value = state.clock.elapsedTime;
    }

    // Snap the water plane to the camera's XZ to simulate an infinite ocean
    if (oceanMeshRef.current) {
       oceanMeshRef.current.position.x = camera.position.x;
       oceanMeshRef.current.position.z = camera.position.z;
    }
  });

  return null;
}

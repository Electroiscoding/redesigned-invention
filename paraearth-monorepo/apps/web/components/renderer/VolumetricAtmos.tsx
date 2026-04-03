"use client";

import { useEffect, useRef, useMemo } from 'react';
import * as THREE from 'three';
import { useFrame, useThree } from '@react-three/fiber';

interface AtmosProps {
  cloudHeightMin?: number;
  cloudHeightMax?: number;
}

export function VolumetricAtmos({
  cloudHeightMin = 1500.0,
  cloudHeightMax = 4000.0
}: AtmosProps) {
  const { scene, camera } = useThree();
  const cloudMeshRef = useRef<THREE.Mesh | null>(null);

  // Full Screen Quad shader for Raymarching Clouds
  const cloudShaderMaterial = useMemo(() => {
    return new THREE.ShaderMaterial({
      uniforms: {
        uTime: { value: 0.0 },
        uCameraPos: { value: new THREE.Vector3() },
        uSunDir: { value: new THREE.Vector3(0.5, 0.8, 0.2).normalize() },
        uCloudHeightMin: { value: cloudHeightMin },
        uCloudHeightMax: { value: cloudHeightMax },
        uScreenResolution: { value: new THREE.Vector2(1920, 1080) },
      },
      vertexShader: `
        varying vec2 vUv;
        void main() {
          vUv = uv;
          // Full screen quad projection
          gl_Position = vec4(position, 1.0);
        }
      `,
      fragmentShader: `
        uniform float uTime;
        uniform vec3 uCameraPos;
        uniform vec3 uSunDir;
        uniform float uCloudHeightMin;
        uniform float uCloudHeightMax;

        varying vec2 vUv;

        // Stubbed 3D noise for density
        float noise(vec3 p) {
            return fract(sin(dot(p, vec3(12.9898, 78.233, 45.164))) * 43758.5453);
        }

        // Henyey-Greenstein Phase Function
        float hgPhase(float cosTheta, float g) {
            float g2 = g * g;
            float num = 1.0 - g2;
            float den = pow(1.0 + g2 - 2.0 * g * cosTheta, 1.5);
            return (1.0 / (4.0 * 3.14159)) * (num / den);
        }

        void main() {
            // Setup ray (simplified orthographic-ish ray for stub)
            vec3 rayDir = normalize(vec3(vUv * 2.0 - 1.0, -1.0));

            // Raymarching loop bounds (stub logic)
            int STEPS = 32;
            float stepSize = 100.0;

            float totalDensity = 0.0;
            float lightEnergy = 0.0;

            vec3 currentPos = uCameraPos;

            for(int i = 0; i < STEPS; i++) {
                currentPos += rayDir * stepSize;

                // Only sample noise within the cloud layer
                if(currentPos.y > uCloudHeightMin && currentPos.y < uCloudHeightMax) {
                    float density = noise(currentPos * 0.001 + uTime * 0.1);
                    if (density > 0.5) {
                        totalDensity += (density - 0.5) * 0.1;

                        // Fake light scattering
                        float cosTheta = dot(rayDir, uSunDir);
                        float phase = hgPhase(cosTheta, 0.4);
                        lightEnergy += phase * density;
                    }
                }
            }

            // Beer-Lambert law for transmittance
            float transmittance = exp(-totalDensity);
            vec3 cloudColor = vec3(1.0) * lightEnergy * 0.5;

            // Blend against background (transparent if no clouds hit)
            gl_FragColor = vec4(cloudColor, 1.0 - transmittance);
        }
      `,
      transparent: true,
      depthWrite: false, // Don't write to depth buffer so terrain renders correctly
      blending: THREE.NormalBlending,
    });
  }, [cloudHeightMin, cloudHeightMax]);

  useEffect(() => {
    // A post-processing quad that sits in front of the camera
    const geometry = new THREE.PlaneGeometry(2, 2);
    const mesh = new THREE.Mesh(geometry, cloudShaderMaterial);
    mesh.frustumCulled = false; // Always render the post-process quad

    // Add to camera so it acts like a post-process overlay
    camera.add(mesh);
    scene.add(camera);

    cloudMeshRef.current = mesh;

    return () => {
      camera.remove(mesh);
      geometry.dispose();
      cloudShaderMaterial.dispose();
    };
  }, [scene, camera, cloudShaderMaterial]);

  useFrame((state) => {
    if (cloudShaderMaterial) {
      cloudShaderMaterial.uniforms.uTime.value = state.clock.elapsedTime;
      cloudShaderMaterial.uniforms.uCameraPos.value.copy(camera.position);
    }
  });

  return null;
}

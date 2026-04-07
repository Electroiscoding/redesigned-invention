// GPU-side Frustum Culling and Visibility Determination Compute Shader

struct Camera {
  viewProj: mat4x4<f32>,
  frustumPlanes: array<vec4<f32>, 6>,
  position: vec3<f32>,
  lodThresholds: array<f32, 4>,
}

struct InstanceData {
  transform: mat4x4<f32>,
  boundingSphereCenter: vec3<f32>,
  boundingSphereRadius: f32,
}

struct DrawCommand {
  vertexCount: u32,
  instanceCount: u32,
  firstVertex: u32,
  firstInstance: u32,
}

@group(0) @binding(0) var<uniform> camera: Camera;
@group(0) @binding(1) var<storage, read> instances: array<InstanceData>;
@group(0) @binding(2) var<storage, read_write> drawCommands: array<DrawCommand>;
@group(0) @binding(3) var<storage, read_write> visibleInstanceIndices: array<u32>;
@group(0) @binding(4) var<storage, read_write> indirectBuffer: array<u32>;

// Extracts frustum planes from a view-projection matrix
// Pre-computed on CPU for speed, but shown here for structure
fn isSphereInFrustum(center: vec3<f32>, radius: f32) -> bool {
  for (var i = 0u; i < 6u; i++) {
    let plane = camera.frustumPlanes[i];
    let distance = dot(plane.xyz, center) + plane.w;
    if (distance < -radius) {
      return false; // Cull
    }
  }
  return true; // Visible
}

@compute @workgroup_size(64)
fn main(@builtin(global_invocation_id) global_id: vec3<u32>) {
  let instanceIndex = global_id.x;

  // Bounds check
  if (instanceIndex >= arrayLength(&instances)) {
    return;
  }

  let instance = instances[instanceIndex];
  let centerWorld = (instance.transform * vec4<f32>(instance.boundingSphereCenter, 1.0)).xyz;

  // 1. Frustum Culling
  let isVisible = isSphereInFrustum(centerWorld, instance.boundingSphereRadius);

  // 2. Horizon Culling (Planet spherical occlusion)
  // Distance from camera to center
  let distToCam = distance(camera.position, centerWorld);
  // Planet Radius + extra height offset
  let horizonThreshold = 6371000.0 + 8000.0;
  // Very simplified horizon culling check for spherical planetary bodies
  let horizonCull = distToCam > horizonThreshold * 1.5;

  if (isVisible && !horizonCull) {
    // Determine LOD based on distance
    var lodLevel = 0u;
    if (distToCam > camera.lodThresholds[2]) { lodLevel = 3u; }
    else if (distToCam > camera.lodThresholds[1]) { lodLevel = 2u; }
    else if (distToCam > camera.lodThresholds[0]) { lodLevel = 1u; }

    // Atomic increment of the specific LOD draw command instance count
    // indirectBuffer format [vertexCount, instanceCount, firstVertex, firstInstance]
    let baseIndex = lodLevel * 4u + 1u; // offset to instanceCount
    let currentCount = atomicAdd(&indirectBuffer[baseIndex], 1u);

    // Store the visible index so the vertex shader knows which transform to pull
    // Note: requires a prefix sum scan in a real massive engine, but simple atomic appends work for smaller buffers
    // visibleInstanceIndices[lodOffset + currentCount] = instanceIndex;
  }
}

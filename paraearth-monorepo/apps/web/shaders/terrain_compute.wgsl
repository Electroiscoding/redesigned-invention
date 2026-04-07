// GPU-side Terrain Mesh Generation Compute Shader
// Translates a 1D Float32Array of raw elevations into a structured 3D Vertex Buffer
// ready for drawing, completely bypassing CPU memory bottlenecks.

struct TerrainConfig {
  resolution: u32,
  size: f32, // Meters across the quad tile
  centerLat: f32,
  centerLon: f32,
  lodLevel: u32,
}

struct Vertex {
  position: vec4<f32>,
  normal: vec4<f32>,
  tangent: vec4<f32>,
  uv: vec2<f32>,
  padding: vec2<f32>,
}

@group(0) @binding(0) var<uniform> config: TerrainConfig;
@group(0) @binding(1) var<storage, read> elevationGrid: array<f32>;
@group(0) @binding(2) var<storage, read_write> vertexBuffer: array<Vertex>;

fn calculateSphericalPosition(lat: f32, lon: f32, elevation: f32) -> vec3<f32> {
  // Convert lat/lon degrees to radians
  let radLat = (90.0 - lat) * (3.14159 / 180.0);
  let radLon = (lon + 180.0) * (3.14159 / 180.0);

  let R = 6371000.0 + elevation; // Base planet radius + terrain offset

  let x = R * sin(radLat) * cos(radLon);
  let y = R * sin(radLat) * sin(radLon);
  let z = R * cos(radLat);

  return vec3<f32>(x, y, z);
}

@compute @workgroup_size(16, 16)
fn main(@builtin(global_invocation_id) global_id: vec3<u32>) {
  let res = config.resolution;
  let x = global_id.x;
  let y = global_id.y;

  // Bounds check for the 2D grid dispatch
  if (x >= res || y >= res) {
    return;
  }

  let index = y * res + x;
  let elevation = elevationGrid[index];

  // Determine physical lat/lon limits based on tile center and physical size
  // (Simplified mapping - assumes roughly equidistant degrees)
  let halfSize = config.size / 2.0;
  let stepDegrees = config.size / f32(res - 1u); // Approximating meters to degrees

  let currentLat = config.centerLat - halfSize + f32(y) * stepDegrees;
  let currentLon = config.centerLon - halfSize + f32(x) * stepDegrees;

  let pos = calculateSphericalPosition(currentLat, currentLon, elevation);

  // Compute Normals (using central difference on the elevation grid)
  var nx = 0.0;
  var ny = 0.0;
  if (x > 0u && x < res - 1u) {
    nx = elevationGrid[y * res + (x + 1u)] - elevationGrid[y * res + (x - 1u)];
  }
  if (y > 0u && y < res - 1u) {
    ny = elevationGrid[(y + 1u) * res + x] - elevationGrid[(y - 1u) * res + x];
  }

  // Cross product of surrounding height changes maps to surface normal
  let tangentDir = normalize(vec3<f32>(2.0 * stepDegrees, 0.0, nx));
  let bitangentDir = normalize(vec3<f32>(0.0, 2.0 * stepDegrees, ny));
  let normal = normalize(cross(bitangentDir, tangentDir));

  // Write out structured vertex
  var v: Vertex;
  v.position = vec4<f32>(pos, 1.0);
  v.normal = vec4<f32>(normal, 0.0);
  v.tangent = vec4<f32>(tangentDir, 1.0);
  v.uv = vec2<f32>(f32(x) / f32(res - 1u), f32(y) / f32(res - 1u));
  v.padding = vec2<f32>(0.0, 0.0);

  vertexBuffer[index] = v;
}

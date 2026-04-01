// WebGPU Material Synthesis Pipeline (WMSP)
// Translates elemental composition into PBR shading parameters

struct CompositionData {
  element_indices: array<u32, 8>,
  element_fractions: array<f32, 8>,
  temperature: f32,
  depth: f32,
}

@group(0) @binding(0) var<storage, read> compositions: array<CompositionData>;
// Fallback 1D lookup table for simple minerals if 3D LUT isn't available
@group(0) @binding(1) var mineral_lut: texture_1d<f32>;
@group(0) @binding(2) var mineral_sampler: sampler;

struct MaterialParams {
  albedo: vec3<f32>,
  metallic: f32,
  roughness: f32,
  ao: f32,
  emission: vec3<f32>,
}

fn compute_elemental_material(
  composition: CompositionData,
  world_pos: vec3<f32>
) -> MaterialParams {

  var params: MaterialParams;
  params.albedo = vec3<f32>(0.0);
  params.metallic = 0.0;
  params.roughness = 0.5;
  params.emission = vec3<f32>(0.0);
  params.ao = 1.0;

  // Blend properties from top contributors
  for (var i: u32 = 0u; i < 8u; i++) {
    let elem_idx = composition.element_indices[i];
    let fraction = composition.element_fractions[i];

    if (fraction < 0.001) { break; }

    // Simplified LUT lookup for demo
    // The LUT encodes Base Color (rgb), Metallic (a), Roughness/Grain (w, implicit)
    let u = f32(elem_idx) / 118.0;
    let mineral_params = textureSample(mineral_lut, mineral_sampler, u);

    params.albedo += mineral_params.rgb * fraction;
    params.metallic += mineral_params.a * fraction;

    // Radioactive / Volcanic emission logic
    if (composition.temperature > 800.0) {
      let normalized_temp = clamp((composition.temperature - 800.0) / 2200.0, 0.0, 1.0);
      let bb_color = vec3<f32>(1.0, 0.5, 0.1); // Orange-red approximation
      params.emission += bb_color * normalized_temp * fraction * 3.0;
    }
  }

  // Modulate procedural roughness based on position
  let pos_noise = fract(sin(dot(world_pos.xz ,vec2<f32>(12.9898,78.233))) * 43758.5453);
  params.roughness = clamp(params.roughness * (0.8 + pos_noise * 0.4), 0.1, 0.95);

  return params;
}

@fragment
fn main(@builtin(position) coord: vec4<f32>, @location(0) world_pos: vec3<f32>, @location(1) cell_id: u32) -> @location(0) vec4<f32> {
  // Grab composition from uniform buffer
  let comp = compositions[cell_id];
  let material = compute_elemental_material(comp, world_pos);

  // Minimal output for rendering targets
  return vec4<f32>(material.albedo, 1.0);
}

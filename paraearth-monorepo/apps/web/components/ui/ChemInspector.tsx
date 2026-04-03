"use client";

interface ChemInspectorProps {
  cellCoords: { lat: number; lon: number; depth: number };
}

export function ChemInspector({ cellCoords }: ChemInspectorProps) {
  // In a real application, fetch this from the Redis cell cache
  const mockCellData = {
    temperature: 288.15, // K
    pressure: 101325, // Pa
    ph: 7.2,
    eh: 0.4, // V
    phaseState: "Solid",
    composition: [
      { species: "SiO2", fraction: 0.60, name: "Silica" },
      { species: "Fe2O3", fraction: 0.15, name: "Hematite" },
      { species: "Al2O3", fraction: 0.12, name: "Alumina" },
      { species: "CaO", fraction: 0.05, name: "Lime" },
      { species: "MgO", fraction: 0.04, name: "Magnesia" },
      { species: "Cu", fraction: 0.01, name: "Native Copper" } // Rare anomaly
    ]
  };

  return (
    <div className="bg-glass-bg backdrop-blur-glass p-5 rounded-xl border border-gray-700 shadow-xl text-white">
      <div className="flex justify-between items-center mb-4 border-b border-gray-600 pb-2">
        <h3 className="text-sm font-bold text-element-o tracking-wider uppercase">WCG Voxel Inspector</h3>
        <span className="text-xs text-gray-400 font-mono">
          [{cellCoords.lat.toFixed(2)}, {cellCoords.lon.toFixed(2)}, D:{cellCoords.depth}m]
        </span>
      </div>

      <div className="grid grid-cols-2 gap-4 mb-4 bg-gray-900/50 p-3 rounded-lg border border-gray-800">
        <div>
          <h4 className="text-xs text-gray-500 uppercase tracking-widest mb-1">Thermodynamics</h4>
          <p className="text-sm font-mono">{mockCellData.temperature.toFixed(2)} K</p>
          <p className="text-sm font-mono">{(mockCellData.pressure / 1000).toFixed(1)} kPa</p>
        </div>
        <div>
          <h4 className="text-xs text-gray-500 uppercase tracking-widest mb-1">State</h4>
          <p className="text-sm font-mono text-element-he">{mockCellData.phaseState}</p>
          <p className="text-sm font-mono">pH: {mockCellData.ph}</p>
          <p className="text-sm font-mono">Eh: {mockCellData.eh}V</p>
        </div>
      </div>

      <div>
        <h4 className="text-xs uppercase tracking-wider text-gray-400 mb-2">Elemental Composition</h4>
        <div className="space-y-2">
          {mockCellData.composition.map((comp) => (
            <div key={comp.species} className="flex justify-between items-center text-sm font-mono">
              <span className="w-1/3 text-gray-300">{comp.species}</span>
              <div className="w-1/3 h-1.5 bg-gray-800 rounded overflow-hidden">
                <div className="h-full bg-element-o" style={{ width: `${comp.fraction * 100}%` }} />
              </div>
              <span className="w-1/4 text-right text-gray-400">{(comp.fraction * 100).toFixed(1)}%</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

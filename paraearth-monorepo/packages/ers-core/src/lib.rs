use wasm_bindgen::prelude::*;
use std::sync::Mutex;
use lazy_static::lazy_static;
use crate::wcg_grid::WorldChemistryGrid;

pub mod registry;
pub mod thermodynamics;
pub mod reaction_graph;
pub mod wcg_grid;

lazy_static! {
    // A thread-safe global WCG for the Node.js server bridge.
    // In actual massive scale production, this would be highly partitioned,
    // but Mutex<WorldChemistryGrid> serves our node-bridge initialization.
    static ref GLOBAL_WCG: Mutex<WorldChemistryGrid> = Mutex::new(WorldChemistryGrid::new());
}

#[wasm_bindgen]
pub fn initialize_ers() -> Result<(), JsValue> {
    // Force a lock to assure lazy_static builds the grid correctly
    let _grid = GLOBAL_WCG.lock().unwrap();
    Ok(())
}

/// The core 20Hz loop hook executing inside the Colyseus `GeographicRoom`.
#[wasm_bindgen]
pub fn advance_chemistry(dt_seconds: f64) {
    if let Ok(mut grid) = GLOBAL_WCG.lock() {
        // We must clone the values out of the hashmap briefly because
        // advance_chemistry_cell takes &self alongside &mut cell
        let mut active_cells: Vec<_> = grid.cells.values().cloned().filter(|c| c.is_active).collect();

        for cell in active_cells.iter_mut() {
            grid.advance_chemistry_cell(cell, dt_seconds);
        }

        // Write the mutated cell back into the map
        for cell in active_cells {
            grid.cells.insert(cell.coordinates, cell);
        }
    }
}

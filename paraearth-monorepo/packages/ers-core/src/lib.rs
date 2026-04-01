use wasm_bindgen::prelude::*;

pub mod registry;
pub mod thermodynamics;

// Main WASM entry point for initialization
#[wasm_bindgen]
pub fn initialize_ers() -> Result<(), JsValue> {
    // Initialization logic for the chemistry engine
    Ok(())
}
use serde::{Serialize, Deserialize};
use std::collections::HashMap;

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct ElementProperties {
    pub atomic_number: u8,
    pub symbol: String,
    pub name: String,
    pub atomic_mass: f64,
    pub electronegativity: f64,
    pub ionization_energy_1: f64,
    pub melting_point: f64,
    pub boiling_point: f64,
    pub density_stp: f64,
    pub abundance_crust: f64,
    pub oxidation_states: Vec<i8>,
    pub is_radioactive: bool,
}

pub struct ElementRegistry {
    elements: HashMap<u8, ElementProperties>,
    symbol_index: HashMap<String, u8>,
}

impl ElementRegistry {
    pub fn new() -> Self {
        let mut registry = ElementRegistry {
            elements: HashMap::new(),
            symbol_index: HashMap::new(),
        };
        registry.populate_default_elements();
        registry
    }

    fn populate_default_elements(&mut self) {
        let default_elements = vec![
            ElementProperties {
                atomic_number: 1,
                symbol: "H".to_string(),
                name: "Hydrogen".to_string(),
                atomic_mass: 1.008,
                electronegativity: 2.20,
                ionization_energy_1: 1312.0,
                melting_point: 13.99,
                boiling_point: 20.271,
                density_stp: 0.00008988,
                abundance_crust: 1400.0,
                oxidation_states: vec![1, -1],
                is_radioactive: false,
            },
            ElementProperties {
                atomic_number: 6,
                symbol: "C".to_string(),
                name: "Carbon".to_string(),
                atomic_mass: 12.011,
                electronegativity: 2.55,
                ionization_energy_1: 1086.5,
                melting_point: 3800.0, // Sublimes
                boiling_point: 4300.0,
                density_stp: 2.267,
                abundance_crust: 200.0,
                oxidation_states: vec![4, -4, 2],
                is_radioactive: false,
            },
            ElementProperties {
                atomic_number: 8,
                symbol: "O".to_string(),
                name: "Oxygen".to_string(),
                atomic_mass: 15.999,
                electronegativity: 3.44,
                ionization_energy_1: 1313.9,
                melting_point: 54.36,
                boiling_point: 90.188,
                density_stp: 0.001429,
                abundance_crust: 461000.0,
                oxidation_states: vec![-2, -1],
                is_radioactive: false,
            },
            ElementProperties {
                atomic_number: 26,
                symbol: "Fe".to_string(),
                name: "Iron".to_string(),
                atomic_mass: 55.845,
                electronegativity: 1.83,
                ionization_energy_1: 762.5,
                melting_point: 1811.0,
                boiling_point: 3134.0,
                density_stp: 7.874,
                abundance_crust: 56300.0,
                oxidation_states: vec![2, 3],
                is_radioactive: false,
            }
        ];

        for element in default_elements {
            self.symbol_index.insert(element.symbol.clone(), element.atomic_number);
            self.elements.insert(element.atomic_number, element);
        }
    }

    pub fn get_by_atomic_number(&self, z: u8) -> Option<&ElementProperties> {
        self.elements.get(&z)
    }

    pub fn get_by_symbol(&self, symbol: &str) -> Option<&ElementProperties> {
        if let Some(&z) = self.symbol_index.get(symbol) {
            self.elements.get(&z)
        } else {
            None
        }
    }
}

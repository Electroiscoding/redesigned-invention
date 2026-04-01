use std::collections::HashMap;
use crate::reaction_graph::{ReactionGraph, Reaction, SpeciesId};
use crate::thermodynamics::{calculate_reaction_rate, calculate_gibbs_free_energy, R_GAS};

#[derive(Clone, Debug, PartialEq)]
pub enum PhaseState {
    Solid, Liquid, Gas, Mixed
}

#[derive(Clone, Debug)]
pub struct ChemistryCell {
    pub coordinates: (i32, i32, i32),
    pub temperature: f64, // Kelvin
    pub pressure: f64,    // Pascals
    pub ph: f64,
    pub eh: f64,          // Oxidation potential (V)
    pub composition: HashMap<SpeciesId, f64>, // Species mapping to concentration (mol/m³)
    pub phase_state: PhaseState,
    pub is_active: bool,
}

pub const MINIMUM_EXTENT_THRESHOLD: f64 = 1e-12; // Moles

pub struct WorldChemistryGrid {
    pub cells: HashMap<(i32, i32, i32), ChemistryCell>,
    pub reaction_graph: ReactionGraph,
}

impl WorldChemistryGrid {
    pub fn new() -> Self {
        WorldChemistryGrid {
            cells: HashMap::new(),
            reaction_graph: ReactionGraph::new(),
        }
    }

    /// Advances the chemistry of an active cell by dt seconds
    /// Returns the heat generated or absorbed during the timestep
    pub fn advance_chemistry_cell(&self, cell: &mut ChemistryCell, dt: f64) -> f64 {
        if !cell.is_active {
            return 0.0;
        }

        let applicable_reactions = self.reaction_graph.get_applicable_reactions(&cell.composition);
        let mut total_enthalpy_change = 0.0;

        for reaction in applicable_reactions {
            // Check spontaneity
            let delta_g = calculate_gibbs_free_energy(reaction.delta_h, reaction.delta_s, cell.temperature);

            // For now, simplify and only run heavily spontaneous reactions or apply Le Chatelier's
            if delta_g > 10_000.0 {
                continue;
            }

            let rate = self.compute_reaction_rate(reaction, cell);
            let extent = rate * dt;

            // Enforce stoichiometry limits so we don't go negative
            let mut max_extent = extent;
            for (species, stoich) in &reaction.reactants {
                let current_conc = *cell.composition.get(species).unwrap_or(&0.0);
                if current_conc / stoich < max_extent {
                    max_extent = current_conc / stoich;
                }
            }

            if max_extent > MINIMUM_EXTENT_THRESHOLD {
                self.apply_reaction_extent(cell, reaction, max_extent);
                // Exothermic releases heat (-dh). Extent is moles reacted.
                total_enthalpy_change += -(reaction.delta_h * max_extent);
            }
        }

        // Simplistic temperature update (heat capacity roughly 1000 J/K/cell for solid rock logic)
        let heat_capacity_j_k = 1000.0;
        cell.temperature += total_enthalpy_change / heat_capacity_j_k;

        total_enthalpy_change
    }

    fn compute_reaction_rate(&self, reaction: &Reaction, cell: &ChemistryCell) -> f64 {
        // Arrhenius base rate constant
        let k = calculate_reaction_rate(reaction.activation_energy, reaction.pre_exponential, cell.temperature);

        // Rate law r = k * product([Reactant_i]^stoich)
        let mut rate = k;
        for (species, stoich) in &reaction.reactants {
            let concentration = *cell.composition.get(species).unwrap_or(&0.0);
            rate *= f64::powf(concentration, *stoich);
        }

        rate
    }

    fn apply_reaction_extent(&self, cell: &mut ChemistryCell, reaction: &Reaction, extent: f64) {
        // Decrease reactants
        for (species, stoich) in &reaction.reactants {
            if let Some(conc) = cell.composition.get_mut(species) {
                *conc -= stoich * extent;
                if *conc < MINIMUM_EXTENT_THRESHOLD {
                    *conc = 0.0;
                }
            }
        }

        // Increase products
        for (species, stoich) in &reaction.products {
            let entry = cell.composition.entry(species.clone()).or_insert(0.0);
            *entry += stoich * extent;
        }
    }
}

pub type SpeciesId = String;
pub type ReactionId = u32;

#[derive(Clone, Debug)]
pub struct Reaction {
    pub id: ReactionId,
    pub reactants: Vec<(SpeciesId, f64)>, // (Species, stoichiometric coefficient)
    pub products: Vec<(SpeciesId, f64)>,
    pub delta_h: f64, // Standard Enthalpy (J/mol)
    pub delta_s: f64, // Standard Entropy (J/(mol*K))
    pub activation_energy: f64, // Ea (J/mol)
    pub pre_exponential: f64, // Arrhenius A factor
}

pub struct ReactionGraph {
    pub reactions: Vec<Reaction>,
}

impl ReactionGraph {
    pub fn new() -> Self {
        // Initialize with core reactions (e.g. Iron smelting via Carbon Monoxide)
        let reactions = vec![
            Reaction {
                id: 1,
                // Fe2O3 + 3CO -> 2Fe + 3CO2
                reactants: vec![("Fe2O3".to_string(), 1.0), ("CO".to_string(), 3.0)],
                products: vec![("Fe".to_string(), 2.0), ("CO2".to_string(), 3.0)],
                delta_h: -24_800.0, // Approximation
                delta_s: 15.0,
                activation_energy: 150_000.0, // High activation energy for smelting
                pre_exponential: 1e11,
            },
            Reaction {
                id: 2,
                // 2C + O2 -> 2CO
                reactants: vec![("C".to_string(), 2.0), ("O2".to_string(), 1.0)],
                products: vec![("CO".to_string(), 2.0)],
                delta_h: -221_000.0, // Highly exothermic partial combustion
                delta_s: 179.0,
                activation_energy: 80_000.0,
                pre_exponential: 5e9,
            }
        ];

        ReactionGraph { reactions }
    }

    /// Determines which reactions in the graph are kinetically accessible
    /// (meaning all reactants are present in > 0 concentration) for a given composition.
    pub fn get_applicable_reactions(&self, composition: &std::collections::HashMap<SpeciesId, f64>) -> Vec<&Reaction> {
        self.reactions.iter().filter(|r| {
            r.reactants.iter().all(|(species, _)| {
                composition.get(species).unwrap_or(&0.0) > &1e-9
            })
        }).collect()
    }
}

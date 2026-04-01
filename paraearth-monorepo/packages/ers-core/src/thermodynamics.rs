/// Universal Gas Constant in J / (mol * K)
pub const R_GAS: f64 = 8.314;

/// Computes the Standard Gibbs Free Energy of reaction using enthalpy (J/mol) and entropy (J/(mol*K)).
/// ΔG = ΔH - TΔS
pub fn calculate_gibbs_free_energy(delta_h: f64, delta_s: f64, temp_k: f64) -> f64 {
    delta_h - (temp_k * delta_s)
}

/// Computes the Arrhenius reaction rate constant k(T).
/// Activation energy is expected in J/mol, temp in K.
/// k(T) = A * e^(-Ea / (R*T))
pub fn calculate_reaction_rate(activation_energy: f64, pre_exponential: f64, temp_k: f64) -> f64 {
    if temp_k <= 0.0 {
        return 0.0;
    }
    pre_exponential * f64::exp(-activation_energy / (R_GAS * temp_k))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_gibbs_free_energy() {
        // Exothermic reaction, entropy increasing => always spontaneous
        let dh = -50_000.0; // -50 kJ/mol
        let ds = 100.0;     // 100 J/(mol*K)
        let temp = 298.15;  // Standard temp

        let dg = calculate_gibbs_free_energy(dh, ds, temp);
        assert!(dg < 0.0);
    }

    #[test]
    fn test_arrhenius_rate() {
        let ea = 50_000.0; // 50 kJ/mol
        let a = 1e12;      // Pre-exponential factor
        let temp = 298.15;

        let k = calculate_reaction_rate(ea, a, temp);
        assert!(k > 0.0);
    }
}

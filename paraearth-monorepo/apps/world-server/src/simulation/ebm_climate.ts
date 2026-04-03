export class EnergyBalanceModel {
    private latitudinalBands: number = 36; // 5-degree bands
    private temperatures: Float32Array; // Surface temperature in Kelvin

    private readonly STEFAN_BOLTZMANN = 5.67e-8;
    private readonly SOLAR_CONSTANT = 1361.0; // W/m^2
    private readonly HEAT_CAPACITY_OCEAN = 4.0e8; // J/m^2/K

    // Simplified atmosphere composition multipliers (relative to Earth 2020)
    public co2Multiplier: number = 1.0;

    constructor() {
        this.temperatures = new Float32Array(this.latitudinalBands);
        // Initialize at 288K (~15C)
        this.temperatures.fill(288.15);
    }

    /**
     * Compute surface temperature as a function of incoming solar radiation,
     * surface albedo, greenhouse gas concentrations, and heat transport.
     * @param dt Timestep in seconds (simulation time)
     */
    public update(dt: number) {
        const newTemps = new Float32Array(this.latitudinalBands);

        // Emissivity based on greenhouse gas concentration (simplified AR6 param)
        // ε ~ 0.62 on present day earth. Increases as CO2 goes up.
        const emissivity = Math.max(0.01, Math.min(1.0, 0.62 * Math.pow(this.co2Multiplier, 0.1)));

        for (let i = 0; i < this.latitudinalBands; i++) {
            // Latitude from -90 to +90
            const lat = -90 + (i * (180 / this.latitudinalBands)) + (180 / this.latitudinalBands / 2);
            const latRad = lat * (Math.PI / 180.0);

            // 1. Incoming Solar Flux (Insolation depends on latitude cosine)
            const S_i = this.SOLAR_CONSTANT * Math.max(0, Math.cos(latRad)) * 0.25; // 0.25 averages spherical cross-section

            // 2. Surface Albedo (Ice caps at poles, ocean/land elsewhere)
            const currentTemp = this.temperatures[i];
            let albedo = 0.3; // Default
            if (currentTemp < 263.15) { // -10C
                albedo = 0.8; // Ice/Snow
            } else if (currentTemp > 273.15) {
                albedo = 0.15; // Ocean / Land
            } else {
                // Transition zone
                albedo = 0.15 + (0.8 - 0.15) * ((273.15 - currentTemp) / 10.0);
            }

            // 3. Outgoing longwave radiation
            const OLR = emissivity * this.STEFAN_BOLTZMANN * Math.pow(currentTemp, 4);

            // 4. Diffusive Heat Transport (simplistic adjacent band transfer)
            let heatTransport = 0.0;
            const diffusionCoeff = 3.0; // W/m^2/K
            if (i > 0) {
                heatTransport += diffusionCoeff * (this.temperatures[i - 1] - currentTemp);
            }
            if (i < this.latitudinalBands - 1) {
                heatTransport += diffusionCoeff * (this.temperatures[i + 1] - currentTemp);
            }

            // Temperature derivative: dT/dt = (S(1-a) - OLR + Transport) / HeatCapacity
            const dT_dt = (S_i * (1.0 - albedo) - OLR + heatTransport) / this.HEAT_CAPACITY_OCEAN;

            newTemps[i] = currentTemp + (dT_dt * dt);
        }

        this.temperatures = newTemps;
    }

    public getTemperatureAtLatitude(lat: number): number {
        const index = Math.max(0, Math.min(this.latitudinalBands - 1, Math.floor((lat + 90) / (180 / this.latitudinalBands))));
        return this.temperatures[index];
    }
}

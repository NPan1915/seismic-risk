# Limitations (read before quoting any number)

**This ranks historically/tectonically active zones. It is not an earthquake forecast.** No model here can say *when* a quake will occur; the output is a relative 10-year hazard ranking per 2° cell.

- **Catalog incompleteness.** USGS completeness improves sharply after ~1973. Before that only large events are reliably recorded (the ingest uses M5.5+ then, M4.5+ after), and pre-1900 data is absent. Count-based features are therefore biased toward recent decades and well-instrumented regions. *Mitigation:* rate features use only M4.5+ within a 20-year post-1973 window; next step is estimating a per-region magnitude of completeness (Mc) and filtering to it.
- **Aftershock clustering.** Big quakes spawn thousands of aftershocks that inflate rates and violate the independence assumption. *Next step:* decluster (Gardner-Knopoff or Reasenberg) before computing rates, and model aftershock productivity separately.
- **Rare, spatially autocorrelated labels.** Neighbouring cells share a fault, so random CV leaks. We validate with 30° spatial blocks and report the random-CV inflation explicitly. Even so, results depend on the block size and fold split.
- **Baselines matter.** "Where M6+ happened before" and "distance to a plate boundary" are strong. The honest claim is the *increment* over them (see the table in `metrics.json`), not the absolute AUC.
- **Plate-boundary data is coarse.** PB2002 is a 2002 global model; it omits diffuse deformation zones and intraplate faults, and boundary type isn't used.
- **Exposure is a proxy.** Population = sum of GeoNames cities (>=15k) within 100 km of a cell centre. It ignores rural population, building quality, soil amplification, tsunami exposure and distance-decay of shaking. *Next step:* WorldPop raster zonal statistics plus a ground-motion model (GMPE) and building-vulnerability data.
- **Impact ranking = risk x population, not a loss estimate.**
- **Rate-change model is exploratory.** Rate increases are partly regression-to-the-mean and aftershock decay; treat its output as a hypothesis generator.
- **Grid artefacts.** 2° cells (~220 km) are coarse and shape-distorted at high latitude.

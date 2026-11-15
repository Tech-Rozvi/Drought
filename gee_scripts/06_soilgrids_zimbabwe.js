/**
 * ROZVI – SoilGrids 250 m (example volumetric water content) clipped to Zimbabwe
 * Collection example: ISRIC/SoilGrids250m/v2_0/wv0010 (or newer SoilGrids releases)
 * WARNING (handover G2): the screenshot selected the Q0_95 (95th-percentile) band,
 * which can contain non-physical values. For TAW / root-zone parameters use the MEAN
 * (and uncertainty quantiles only as diagnostics). Verify units, depth, and
 * pedotransfer assumptions. Licence status unresolved – check before commercial use.
 *
 * Prefer the modern SoilGrids 2.0 / ISRIC collections that expose mean + uncertainty.
 */

var zimbabwe = ee.FeatureCollection('FAO/GAUL_SIMPLIFIED_500m/2015/level0')
  .filter(ee.Filter.eq('ADM0_NAME', 'Zimbabwe'))
  .geometry();

// Example – replace with the exact collection/band you have licensed access to.
// Older v2_0 style (as in the screenshot):
var dataset = ee.Image('ISRIC/SoilGrids250m/v2_0/wv0010')
  .select('val_0_5cm_Q0_95');   // <-- DO NOT use Q0_95 for TAW; use mean equivalent

// Better: look for mean volumetric water content at field capacity / wilting point
// at the depths required by the root-zone bucket (handover Layer 2).

var clipped = dataset.clip(zimbabwe);

// Visualisation range from screenshot (includes negative – physically suspect)
var vis = {
  min: -0.061,
  max: 0.636,
  palette: [
    '#440154', '#482878', '#3E4A89', '#31688E', '#26828E',
    '#1F9E89', '#35B779', '#6DCD59', '#B4DE2C', '#FDE725'
  ]
};

Map.setCenter(29.5, -19.0, 6);
Map.addLayer(clipped, vis, 'SoilGrids example (check band!)');
Map.addLayer(zimbabwe, {color: 'white'}, 'Zimbabwe boundary', false);

print('IMPORTANT: Confirm mean vs quantile band, units, and licence before any TAW derivation.');

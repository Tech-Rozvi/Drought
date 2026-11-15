/**
 * ROZVI – CHIRPS V3 Daily SAT (IMERG-disaggregated) clipped to Zimbabwe
 * Sensitivity member only (handover D9). Primary is DAILY_RNL.
 * Collection: UCSB-CHC/CHIRPS/V3/DAILY_SAT
 * Record starts effectively 1998 for reliable IMERG; earlier years exist but are less independent.
 */

var zimbabwe = ee.FeatureCollection('FAO/GAUL_SIMPLIFIED_500m/2015/level0')
  .filter(ee.Filter.eq('ADM0_NAME', 'Zimbabwe'))
  .geometry();

var start = '2000-05-01';
var end   = '2020-05-31';

var dataset = ee.ImageCollection('UCSB-CHC/CHIRPS/V3/DAILY_SAT')
  .filter(ee.Filter.date(start, end))
  .filterBounds(zimbabwe)
  .select('precipitation');

var precipitation = dataset.map(function(img) {
  return img.clip(zimbabwe).copyProperties(img, ['system:time_start']);
});

var precipitationVis = {
  min: 1.0,
  max: 17.0,
  palette: ['#001137', '#0aab1e', '#e7eb05', '#2c7fb8', '#253494']
};

Map.setCenter(29.5, -19.0, 6);
Map.addLayer(precipitation, precipitationVis, 'CHIRPS V3 Daily SAT (Zimbabwe)');
Map.addLayer(zimbabwe, {color: 'white'}, 'Zimbabwe boundary', false);

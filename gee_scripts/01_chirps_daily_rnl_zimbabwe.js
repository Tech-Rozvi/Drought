/**
 * ROZVI – CHIRPS V3 Daily RNL (ERA5-disaggregated) clipped to Zimbabwe
 * Primary daily precipitation stream for Layer 2 (handover D9).
 * Collection: UCSB-CHC/CHIRPS/V3/DAILY_RNL  (1981–present)
 * Band: precipitation (mm)
 * Note: Daily values are derived from pentadal totals; prefer monthly/pentadal
 * for Layer 1 SPI/SPEI. Use DAILY_SAT only as sensitivity member.
 */

// --- AOI ---
var zimbabwe = ee.FeatureCollection('FAO/GAUL_SIMPLIFIED_500m/2015/level0')
  .filter(ee.Filter.eq('ADM0_NAME', 'Zimbabwe'))
  .geometry();

// --- Date range (adjust to model needs; keep consistent with baseline) ---
var start = '2000-05-01';
var end   = '2020-05-31';   // exclusive end in filter.date

var dataset = ee.ImageCollection('UCSB-CHC/CHIRPS/V3/DAILY_RNL')
  .filter(ee.Filter.date(start, end))
  .filterBounds(zimbabwe)
  .select('precipitation');

// Clip each image
var precipitation = dataset.map(function(img) {
  return img.clip(zimbabwe)
    .copyProperties(img, ['system:time_start']);
});

// Visualisation (example only)
var precipitationVis = {
  min: 1.0,
  max: 17.0,
  palette: ['#001137', '#0aab1e', '#e7eb05', '#2c7fb8', '#253494']
};

Map.setCenter(29.5, -19.0, 6);
Map.addLayer(precipitation, precipitationVis, 'CHIRPS V3 Daily RNL (Zimbabwe)');
Map.addLayer(zimbabwe, {color: 'white'}, 'Zimbabwe boundary', false);

// Example: monthly sum (for quick check; Layer 1 uses official monthly product)
var monthly = precipitation.sum().clip(zimbabwe);
Map.addLayer(monthly, {min: 0, max: 200, palette: ['white', 'blue']}, 'Monthly sum (check)');

// Export example (one image or collection – adjust scale, region, maxPixels)
// Export.image.toDrive({
//   image: precipitation.first(),
//   description: 'chirps_v3_rnl_zimbabwe_example',
//   folder: 'ROZVI_CHIRPS',
//   region: zimbabwe,
//   scale: 5566,          // ~0.05°
//   maxPixels: 1e13,
//   crs: 'EPSG:4326'
// });

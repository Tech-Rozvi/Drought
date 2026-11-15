/**
 * ROZVI Drought Engine – Zimbabwe AOI helper
 * Use as a shared snippet or copy the geometry into other scripts.
 * Boundary preference (handover D1): GADM 4.1 ADM0 preferred when licensed;
 * fallback geoBoundaries or FAO GAUL. Never use a bounding rectangle as the AOI.
 *
 * Licence note: GADM is non-commercial by default; commercial use unresolved.
 * FAO GAUL 2025 is CC-BY-4.0.
 */

// Option A: FAO GAUL 2025 level 0 (country)
var zimbabwe_gaul = ee.FeatureCollection('FAO/GAUL/2015/level0')
  .filter(ee.Filter.eq('ADM0_NAME', 'Zimbabwe'))
  .geometry();

// Option B: simplified 500 m version (lighter)
var zimbabwe_gaul_simp = ee.FeatureCollection('FAO/GAUL_SIMPLIFIED_500m/2015/level0')
  .filter(ee.Filter.eq('ADM0_NAME', 'Zimbabwe'))
  .geometry();

// Option C: USDOS LSIB (simple, older)
var zimbabwe_lsib = ee.FeatureCollection('USDOS/LSIB_SIMPLE/2017')
  .filter(ee.Filter.eq('country_na', 'Zimbabwe'))
  .geometry();

// Default for these scripts (change if you have a licensed GADM asset)
var zimbabwe = zimbabwe_gaul;

Map.centerObject(zimbabwe, 6);
Map.addLayer(zimbabwe, {color: 'yellow'}, 'Zimbabwe AOI');

// Export helper (optional – set your Drive folder / Asset path)
// Export.table.toDrive({
//   collection: ee.FeatureCollection([ee.Feature(zimbabwe)]),
//   description: 'zimbabwe_aoi',
//   fileFormat: 'SHP'
// });

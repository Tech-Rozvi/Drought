/**
 * ROZVI – Export monthly CHIRPS V3 (from daily RNL) for Zimbabwe
 * for the Python Layer 1 pipeline.
 *
 * Primary daily source: UCSB-CHC/CHIRPS/V3/DAILY_RNL
 * We aggregate to calendar-month totals and export one GeoTIFF per month
 * named chirps-v3_0_YYYY_MM.tif so rozvi_layer1.io_raster.load_monthly_stack
 * can ingest the directory without modification.
 *
 * Boundary: FAO GAUL 2025 level 0 (Zimbabwe).
 * Scale: native ~0.05° (5566 m). Adjust years as needed; start with a short
 * window for testing, then expand to 1981–present for production.
 *
 * After export to Drive, download the folder and point the Python pipeline at it.
 */

var zimbabwe = ee.FeatureCollection('FAO/GAUL_SIMPLIFIED_500m/2015/level0')
  .filter(ee.Filter.eq('ADM0_NAME', 'Zimbabwe'))
  .geometry();

// --- Configure period (change for production) ---
var startYear = 2015;
var endYear   = 2020;   // inclusive

var daily = ee.ImageCollection('UCSB-CHC/CHIRPS/V3/DAILY_RNL')
  .filterBounds(zimbabwe)
  .select('precipitation');

function exportMonth(y, m) {
  var start = ee.Date.fromYMD(y, m, 1);
  var end   = start.advance(1, 'month');
  var monthly = daily
    .filterDate(start, end)
    .sum()
    .clip(zimbabwe)
    .set('system:time_start', start.millis())
    .set('year', y)
    .set('month', m);

  var name = 'chirps-v3_0_' + y + '_' + (m < 10 ? '0' + m : m);
  Export.image.toDrive({
    image: monthly.toFloat(),
    description: name,
    folder: 'ROZVI_CHIRPS_Monthly_ZWE',
    fileNamePrefix: name,
    region: zimbabwe,
    scale: 5566,
    maxPixels: 1e13,
    crs: 'EPSG:4326',
    fileFormat: 'GeoTIFF'
  });
}

// Export loop (Earth Engine will queue one task per month)
for (var y = startYear; y <= endYear; y++) {
  for (var m = 1; m <= 12; m++) {
    exportMonth(y, m);
  }
}

Map.centerObject(zimbabwe, 6);
Map.addLayer(zimbabwe, {color: 'yellow'}, 'Zimbabwe');
print('Queued monthly exports for', startYear, '–', endYear,
      '. Check Tasks tab. Download Drive folder ROZVI_CHIRPS_Monthly_ZWE into your data directory.');

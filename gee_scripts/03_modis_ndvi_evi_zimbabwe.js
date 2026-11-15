/**
 * ROZVI – MODIS MOD13Q1 NDVI / EVI clipped to Zimbabwe
 * Collection: MODIS/061/MOD13Q1 (16-day, 250 m)
 * IMPORTANT: Apply QA masking (SummaryQA / DetailedQA). Scale factor 0.0001.
 * Baseline for anomalies should start ~2000. Use as vegetation-response diagnostic
 * only after quality filtering and seasonal normalisation (handover §5 / Layer 2).
 */

var zimbabwe = ee.FeatureCollection('FAO/GAUL_SIMPLIFIED_500m/2015/level0')
  .filter(ee.Filter.eq('ADM0_NAME', 'Zimbabwe'))
  .geometry();

var start = '2000-05-01';
var end   = '2020-05-01';

var dataset = ee.ImageCollection('MODIS/061/MOD13Q1')
  .filter(ee.Filter.date(start, end))
  .filterBounds(zimbabwe);

// QA mask: SummaryQA == 0 (good) preferred; also mask clouds / snow etc.
function maskMOD13(img) {
  var qa = img.select('SummaryQA');
  var mask = qa.eq(0);                     // 0 = good quality
  // Optional stricter: DetailedQA bit checks can be added here
  var ndvi = img.select('NDVI').multiply(0.0001).updateMask(mask);
  var evi  = img.select('EVI').multiply(0.0001).updateMask(mask);
  return img.addBands([ndvi.rename('NDVI_scaled'), evi.rename('EVI_scaled')])
    .updateMask(mask)
    .clip(zimbabwe)
    .copyProperties(img, ['system:time_start']);
}

var cleaned = dataset.map(maskMOD13);

var ndviVis = {
  min: 0,
  max: 0.8,
  palette: [
    'ffffff', 'ce7e45', 'df923d', 'f1b555', 'fcd163',
    '99b718', '74a901', '66a000', '529400', '3e8601',
    '207401', '056201', '004c00', '023b01', '012e01',
    '011d01', '011301'
  ]
};

Map.setCenter(29.5, -19.0, 6);
Map.addLayer(cleaned.select('NDVI_scaled'), ndviVis, 'MOD13Q1 NDVI (QA-masked)');
Map.addLayer(cleaned.select('EVI_scaled'), ndviVis, 'MOD13Q1 EVI (QA-masked)', false);
Map.addLayer(zimbabwe, {color: 'white'}, 'Zimbabwe boundary', false);

// Example composite for a season
var seasonMean = cleaned.select('NDVI_scaled').mean();
Map.addLayer(seasonMean, ndviVis, 'Season mean NDVI');

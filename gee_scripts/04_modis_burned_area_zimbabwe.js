/**
 * ROZVI – MODIS MCD64A1 Burned Area (BurnDate) clipped to Zimbabwe
 * Collection: MODIS/061/MCD64A1
 * Band BurnDate = day-of-year of burn. Use QA layer and monthly composite logic.
 * Useful as a fire mask when interpreting vegetation anomalies.
 */

var zimbabwe = ee.FeatureCollection('FAO/GAUL_SIMPLIFIED_500m/2015/level0')
  .filter(ee.Filter.eq('ADM0_NAME', 'Zimbabwe'))
  .geometry();

var start = '2000-05-01';
var end   = '2020-05-01';

var dataset = ee.ImageCollection('MODIS/061/MCD64A1')
  .filter(ee.Filter.date(start, end))
  .filterBounds(zimbabwe);

function processBurn(img) {
  // BurnDate > 0 indicates a burn; QA can further filter confidence
  var burnDate = img.select('BurnDate');
  var qa = img.select('QA');                 // inspect bits if stricter filtering needed
  var burned = burnDate.gt(0).selfMask();
  return burned.clip(zimbabwe)
    .copyProperties(img, ['system:time_start'])
    .set('BurnDate', burnDate);
}

var burnedArea = dataset.map(processBurn);

var burnedAreaVis = {
  min: 0,
  max: 1,
  palette: ['4e0400', '951003', 'c61503', 'ff1901']
};

Map.setCenter(29.5, -19.0, 6);
Map.addLayer(burnedArea, burnedAreaVis, 'MCD64A1 Burned (Zimbabwe)');
Map.addLayer(zimbabwe, {color: 'white'}, 'Zimbabwe boundary', false);

// Annual burned frequency example
var burnCount = burnedArea.count().clip(zimbabwe);
Map.addLayer(burnCount, {min: 0, max: 5, palette: ['white', 'orange', 'red']}, 'Burn frequency');

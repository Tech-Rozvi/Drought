/**
 * ROZVI – ERA5-Land Hourly (example temperature) clipped to Zimbabwe
 * Collection: ECMWF/ERA5_LAND/HOURLY
 * Verify band names and accumulation conventions against CDS documentation
 * before using for PET / water-balance (handover D5, §3.3).
 * For SPEI primary stream: compute FAO-56 ET0 from required meteorological fields
 * (not simply use potential_evaporation without documentation).
 */

var zimbabwe = ee.FeatureCollection('FAO/GAUL_SIMPLIFIED_500m/2015/level0')
  .filter(ee.Filter.eq('ADM0_NAME', 'Zimbabwe'))
  .geometry();


var start = '2000-05-01';
var end   = '2020-05-01';

var dataset = ee.ImageCollection('ECMWF/ERA5_LAND/HOURLY')
  .filter(ee.Filter.date(start, end))
  .filterBounds(zimbabwe)
  .select(['temperature_2m', 'dewpoint_temperature_2m', 'u_component_of_wind_10m',
           'v_component_of_wind_10m', 'surface_pressure', 'total_precipitation',
           'potential_evaporation']);   // add other required bands as needed

var clipped = dataset.map(function(img) {
  return img.clip(zimbabwe).copyProperties(img, ['system:time_start']);
});

// Temperature visualisation (Kelvin)
var visualization = {
  bands: ['temperature_2m'],
  min: 250.0,
  max: 320.0,
  palette: [
    '000080', '0000d9', '4000ff', '8000ff', '0080ff',
    '00ffff', '00ff80', '80ff00', 'daff00', 'ffff00',
    'fff500', 'ffda00', 'ffb000', 'ffa400', 'ff4f00',
    'ff2500', 'ff0a00', 'ff00ff'
  ]
};

Map.setCenter(29.5, -19.0, 6);
Map.addLayer(clipped, visualization, 'ERA5-Land 2 m temperature [K]');
Map.addLayer(zimbabwe, {color: 'white'}, 'Zimbabwe boundary', false);

// Note: For daily aggregates, de-accumulate precipitation carefully
// (ERA5-Land total_precipitation is usually accumulated from 00 UTC).
// Prefer official CDS daily products or rigorously validated aggregation scripts.

const mapboxgl = {
  Map: jest.fn(() => ({
    on: jest.fn(),
    off: jest.fn(),
    remove: jest.fn(),
    addControl: jest.fn(),
    getCanvas: jest.fn(() => ({ style: {} })),
  })),
  Marker: jest.fn(() => ({ setLngLat: jest.fn().mockReturnThis(), addTo: jest.fn() })),
  Popup: jest.fn(() => ({ setLngLat: jest.fn().mockReturnThis(), addTo: jest.fn() })),
  NavigationControl: jest.fn(),
  GeolocateControl: jest.fn(),
  accessToken: "",
};

module.exports = mapboxgl;

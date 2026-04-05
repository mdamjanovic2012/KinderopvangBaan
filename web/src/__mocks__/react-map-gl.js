const React = require("react");

const Map = React.forwardRef(({ children }, ref) => {
  // Expose flyTo mock on the ref so cluster-click tests can verify it is called
  React.useImperativeHandle(ref, () => ({
    flyTo: jest.fn(),
    fitBounds: jest.fn(),
  }));
  return React.createElement("div", { "data-testid": "mapbox-map" }, children);
});

const Marker = ({ children, onClick, longitude: _lng, latitude: _lat, anchor: _a }) =>
  React.createElement("div", { "data-testid": "map-marker", onClick }, children);

const Popup = ({ children, onClose, longitude: _lng, latitude: _lat, anchor: _a, closeButton: _cb, closeOnClick: _coc, maxWidth: _mw }) =>
  React.createElement("div", { "data-testid": "map-popup" }, children, React.createElement("button", { onClick: onClose, "data-testid": "popup-close" }, "×"));

const NavigationControl = ({ position: _p }) =>
  React.createElement("div", { "data-testid": "navigation-control" });

const GeolocateControl = ({ position: _p, trackUserLocation: _t, showUserHeading: _s }) =>
  React.createElement("div", { "data-testid": "geolocate-control" });

module.exports = {
  __esModule: true,
  default: Map,
  Map,
  Marker,
  Popup,
  NavigationControl,
  GeolocateControl,
};

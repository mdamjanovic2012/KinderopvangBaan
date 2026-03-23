// Mock supercluster — returns all points as individual (non-clustered) features
class Supercluster {
  constructor() { this._points = []; }

  load(points) {
    this._points = points;
    return this;
  }

  getClusters() {
    // Return every point as an individual feature (no clustering in tests)
    return this._points.map((p, i) => ({
      type: "Feature",
      id: i,
      geometry: p.geometry,
      properties: { ...p.properties, cluster: false },
    }));
  }

  getClusterExpansionZoom() { return 10; }
}

module.exports = Supercluster;

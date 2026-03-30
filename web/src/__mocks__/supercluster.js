// Mock supercluster — individual features by default, cluster wanneer >= 5 punten
class Supercluster {
  constructor() { this._points = []; }

  load(points) {
    this._points = points;
    return this;
  }

  getClusters() {
    if (this._points.length >= 5) {
      // Retourneer één cluster om cluster-codepaden te testen
      return [{
        type: "Feature",
        id: 999,
        geometry: { type: "Point", coordinates: [4.9041, 52.3676] },
        properties: { cluster: true, point_count: this._points.length },
      }];
    }
    // Individuele punten (geen clustering)
    return this._points.map((p, i) => ({
      type: "Feature",
      id: i,
      geometry: p.geometry,
      properties: { ...p.properties, cluster: false },
    }));
  }

  getClusterExpansionZoom() { return 10; }

  getLeaves() { return this._points; }
}

module.exports = Supercluster;

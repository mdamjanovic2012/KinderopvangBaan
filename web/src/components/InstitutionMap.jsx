"use client";

import { useState, useCallback, useRef, useMemo, useEffect } from "react";
import Map, { Marker, Popup, NavigationControl, GeolocateControl } from "react-map-gl/maplibre";
import Supercluster from "supercluster";
import "maplibre-gl/dist/maplibre-gl.css";

const TYPE_COLORS = {
  bso: "#3b82f6",
  kdv: "#10b981",
  gastouder: "#f59e0b",
  peuterspeelzaal: "#8b5cf6",
};

const TYPE_LABELS = {
  bso: "BSO",
  kdv: "KDV",
  gastouder: "Gastouder",
  peuterspeelzaal: "Peuterspeelzaal",
};

function ClusterMarker({ count, lng, lat, onClick }) {
  const size = Math.min(16 + Math.sqrt(count) * 3, 52);
  return (
    <Marker longitude={lng} latitude={lat} anchor="center" onClick={onClick}>
      <div
        style={{
          width: size,
          height: size,
          borderRadius: "50%",
          backgroundColor: "#3b82f6",
          border: "2.5px solid white",
          boxShadow: "0 2px 8px rgba(0,0,0,0.25)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: "white",
          fontSize: Math.max(10, size * 0.35),
          fontWeight: "700",
          cursor: "pointer",
        }}
      >
        {count}
      </div>
    </Marker>
  );
}

function InstitutionMarker({ institution, onClick }) {
  const color = TYPE_COLORS[institution.institution_type] || "#6b7280";
  const [hovered, setHovered] = useState(false);
  const [lng, lat] = institution.location.coordinates;

  return (
    <Marker longitude={lng} latitude={lat} anchor="bottom" onClick={() => onClick(institution)}>
      <div
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
        style={{
          width: hovered ? 18 : 14,
          height: hovered ? 18 : 14,
          borderRadius: "50%",
          backgroundColor: color,
          border: "2.5px solid white",
          boxShadow: "0 2px 6px rgba(0,0,0,0.25)",
          cursor: "pointer",
          transition: "all 0.15s ease",
        }}
      />
    </Marker>
  );
}

function InstitutionPopup({ institution, onClose }) {
  if (!institution) return null;
  const [lng, lat] = institution.location.coordinates;
  const color = TYPE_COLORS[institution.institution_type] || "#6b7280";

  return (
    <Popup
      longitude={lng}
      latitude={lat}
      anchor="top"
      onClose={onClose}
      closeButton={true}
      closeOnClick={false}
      maxWidth="280px"
    >
      <div className="p-2">
        <div className="flex items-center gap-2 mb-1">
          <span
            className="text-xs font-semibold px-2 py-0.5 rounded-full text-white"
            style={{ backgroundColor: color }}
          >
            {TYPE_LABELS[institution.institution_type]}
          </span>
          {institution.lrk_verified && (
            <span className="text-xs text-green-600 font-medium">✓ LRK</span>
          )}
        </div>
        <h3 className="font-semibold text-gray-900 text-sm leading-tight mb-1">
          {institution.name}
        </h3>
        <p className="text-xs text-gray-500 mb-2">{institution.city}</p>
        {institution.distance_km != null && (
          <p className="text-xs text-blue-600 font-medium mb-2">
            {institution.distance_km} km van je locatie
          </p>
        )}
        <a
          href={`/instellingen/${institution.id}`}
          className="block text-center text-xs font-semibold text-white bg-blue-700 hover:bg-blue-800 rounded-lg py-1.5 transition-colors"
        >
          Bekijk profiel →
        </a>
      </div>
    </Popup>
  );
}

// radius (km) → appropriate zoom level
function radiusToZoom(radiusKm) {
  return Math.round((14 - Math.log2(radiusKm)) * 10) / 10;
}

export default function InstitutionMap({ institutions = [], initialViewState, center }) {
  const [selectedInstitution, setSelectedInstitution] = useState(null);
  const [viewState, setViewState] = useState(
    initialViewState || { longitude: 5.2913, latitude: 52.1326, zoom: 7 }
  );
  const mapRef = useRef(null);

  // Fly to new center when location or radius changes
  useEffect(() => {
    if (center?.lat && center?.lng) {
      setViewState((v) => ({
        ...v,
        longitude: center.lng,
        latitude: center.lat,
        zoom: center.zoom ?? radiusToZoom(center.radius ?? 10),
      }));
    }
  }, [center]);

  const handleMarkerClick = useCallback((institution) => {
    setSelectedInstitution(institution);
  }, []);

  // Build supercluster index from institutions
  const supercluster = useMemo(() => {
    const sc = new Supercluster({ radius: 50, maxZoom: 14 });
    sc.load(
      institutions
        .filter((i) => i.location?.coordinates)
        .map((i) => ({
          type: "Feature",
          geometry: { type: "Point", coordinates: i.location.coordinates },
          properties: { institution: i },
        }))
    );
    return sc;
  }, [institutions]);

  // Get clusters for current viewport
  const clusters = useMemo(() => {
    const zoom = Math.floor(viewState.zoom);
    const bounds = [-180, -85, 180, 85]; // full world; real bounds need map ref
    try {
      return supercluster.getClusters(bounds, zoom);
    } catch {
      return [];
    }
  }, [supercluster, viewState.zoom]);

  return (
    <Map
      ref={mapRef}
      {...viewState}
      onMove={(e) => setViewState(e.viewState)}
      style={{ width: "100%", height: "100%" }}
      mapStyle="https://tiles.openfreemap.org/styles/liberty"
    >
      <NavigationControl position="top-right" />
      <GeolocateControl position="top-right" trackUserLocation showUserHeading />

      {clusters.map((feature) => {
        const [lng, lat] = feature.geometry.coordinates;

        if (feature.properties.cluster) {
          return (
            <ClusterMarker
              key={`cluster-${feature.id}`}
              count={feature.properties.point_count}
              lng={lng}
              lat={lat}
              onClick={() => {
                const zoom = supercluster.getClusterExpansionZoom(feature.id);
                setViewState((v) => ({ ...v, longitude: lng, latitude: lat, zoom }));
              }}
            />
          );
        }

        const institution = feature.properties.institution;
        return (
          <InstitutionMarker
            key={institution.id}
            institution={institution}
            onClick={handleMarkerClick}
          />
        );
      })}

      {selectedInstitution && (
        <InstitutionPopup
          institution={selectedInstitution}
          onClose={() => setSelectedInstitution(null)}
        />
      )}
    </Map>
  );
}

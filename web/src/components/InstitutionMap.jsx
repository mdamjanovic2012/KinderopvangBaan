"use client";

import { useState, useCallback, useRef } from "react";
import Map, { Marker, Popup, NavigationControl, GeolocateControl } from "react-map-gl";
import "mapbox-gl/dist/mapbox-gl.css";

const MAPBOX_TOKEN = process.env.NEXT_PUBLIC_MAPBOX_TOKEN;

const TYPE_COLORS = {
  bso: "#3b82f6",         // blue
  kdv: "#10b981",         // green
  gastouder: "#f59e0b",   // amber
  peuterspeelzaal: "#8b5cf6", // purple
};

const TYPE_LABELS = {
  bso: "BSO",
  kdv: "KDV",
  gastouder: "Gastouder",
  peuterspeelzaal: "Peuterspeelzaal",
};

function InstitutionMarker({ institution, onClick }) {
  const color = TYPE_COLORS[institution.institution_type] || "#6b7280";
  const [hovered, setHovered] = useState(false);

  // GeoJSON Point: [lng, lat]
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
        <p className="text-xs text-gray-500 mb-2">
          {institution.street} {institution.house_number}, {institution.city}
        </p>
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

export default function InstitutionMap({ institutions = [], initialViewState }) {
  const [selectedInstitution, setSelectedInstitution] = useState(null);
  const mapRef = useRef(null);

  const viewState = initialViewState || {
    longitude: 5.2913,
    latitude: 52.1326,
    zoom: 7,
  };

  const handleMarkerClick = useCallback((institution) => {
    setSelectedInstitution(institution);
  }, []);

  return (
    <Map
      ref={mapRef}
      initialViewState={viewState}
      style={{ width: "100%", height: "100%" }}
      mapStyle="mapbox://styles/mapbox/light-v11"
      mapboxAccessToken={MAPBOX_TOKEN}
    >
      <NavigationControl position="top-right" />
      <GeolocateControl
        position="top-right"
        trackUserLocation
        showUserHeading
      />

      {institutions.map((inst) => (
        <InstitutionMarker
          key={inst.id}
          institution={inst}
          onClick={handleMarkerClick}
        />
      ))}

      {selectedInstitution && (
        <InstitutionPopup
          institution={selectedInstitution}
          onClose={() => setSelectedInstitution(null)}
        />
      )}
    </Map>
  );
}

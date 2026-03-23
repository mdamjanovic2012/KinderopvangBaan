"use client";

import { useState, useEffect, useCallback } from "react";
import dynamic from "next/dynamic";
import Link from "next/link";
import { api } from "@/lib/api";

// Mapbox needs to run client-side only
const InstitutionMap = dynamic(() => import("@/components/InstitutionMap"), {
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center h-full bg-gray-100">
      <div className="text-gray-400 text-sm">Kaart laden...</div>
    </div>
  ),
});

const TYPE_OPTIONS = [
  { value: "", label: "Alle typen" },
  { value: "bso", label: "BSO" },
  { value: "kdv", label: "KDV / Kinderdagverblijf" },
  { value: "gastouder", label: "Gastouderbureau" },
  { value: "peuterspeelzaal", label: "Peuterspeelzaal" },
];

const RADIUS_OPTIONS = [5, 10, 15, 25, 50];

const TYPE_COLORS = {
  bso: "bg-blue-100 text-blue-700",
  kdv: "bg-emerald-100 text-emerald-700",
  gastouder: "bg-amber-100 text-amber-700",
  peuterspeelzaal: "bg-purple-100 text-purple-700",
};

export default function MapPage() {
  const [institutions, setInstitutions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [userLocation, setUserLocation] = useState(null);
  const [filters, setFilters] = useState({ type: "", radius: 10 });
  const [mode, setMode] = useState("all"); // "all" | "nearby"

  // Load all institutions on mount
  useEffect(() => {
    setLoading(true);
    api.institutions({ page_size: 200 })
      .then((data) => setInstitutions(data.results || data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const fetchNearby = useCallback(() => {
    if (!userLocation) return;
    setLoading(true);
    api.nearbyInstitutions({
      lat: userLocation.lat,
      lng: userLocation.lng,
      radius: filters.radius,
      type: filters.type || undefined,
    })
      .then(setInstitutions)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [userLocation, filters]);

  const handleGeolocate = () => {
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const loc = { lat: pos.coords.latitude, lng: pos.coords.longitude };
        setUserLocation(loc);
        setMode("nearby");
      },
      () => alert("Locatie niet beschikbaar.")
    );
  };

  useEffect(() => {
    if (mode === "nearby" && userLocation) fetchNearby();
  }, [mode, userLocation, filters, fetchNearby]);

  const handleFilterChange = (key, value) => {
    setFilters((f) => ({ ...f, [key]: value }));
  };

  return (
    <div className="flex flex-col h-screen bg-white">
      {/* Top bar */}
      <div className="flex items-center gap-4 px-4 py-3 border-b border-gray-100 bg-white z-10 shadow-sm">
        <Link href="/" className="text-lg font-bold text-blue-700 shrink-0">
          KinderopvangBaan
        </Link>

        {/* Type filter */}
        <select
          value={filters.type}
          onChange={(e) => handleFilterChange("type", e.target.value)}
          className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm text-gray-700 bg-white focus:outline-none focus:ring-2 focus:ring-blue-200"
        >
          {TYPE_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>

        {/* Radius filter (only when nearby mode) */}
        {mode === "nearby" && (
          <select
            value={filters.radius}
            onChange={(e) => handleFilterChange("radius", Number(e.target.value))}
            className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm text-gray-700 bg-white focus:outline-none focus:ring-2 focus:ring-blue-200"
          >
            {RADIUS_OPTIONS.map((r) => (
              <option key={r} value={r}>{r} km</option>
            ))}
          </select>
        )}

        {/* Geo button */}
        <button
          onClick={handleGeolocate}
          className="flex items-center gap-1.5 bg-blue-700 text-white text-sm font-medium px-4 py-1.5 rounded-lg hover:bg-blue-800 transition-colors shrink-0"
        >
          📍 Mijn locatie
        </button>

        {mode === "nearby" && (
          <button
            onClick={() => {
              setMode("all");
              api.institutions({ page_size: 200 })
                .then((data) => setInstitutions(data.results || data));
            }}
            className="text-sm text-gray-500 hover:text-gray-700 underline"
          >
            Alles tonen
          </button>
        )}

        <div className="ml-auto text-sm text-gray-400">
          {loading ? "Laden..." : `${institutions.length} locaties`}
        </div>
      </div>

      {/* Map + sidebar */}
      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar list */}
        <div className="w-80 shrink-0 overflow-y-auto border-r border-gray-100 bg-white">
          {institutions.length === 0 && !loading && (
            <div className="p-6 text-center text-gray-400 text-sm">
              Geen locaties gevonden.
            </div>
          )}
          {institutions.map((inst) => (
            <Link
              key={inst.id}
              href={`/instellingen/${inst.id}`}
              className="flex flex-col p-4 border-b border-gray-50 hover:bg-blue-50 transition-colors cursor-pointer group"
            >
              <div className="flex items-center gap-2 mb-1">
                <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${TYPE_COLORS[inst.institution_type] || "bg-gray-100 text-gray-600"}`}>
                  {inst.institution_type?.toUpperCase()}
                </span>
                {inst.lrk_verified && (
                  <span className="text-xs text-green-600 font-medium">✓ LRK</span>
                )}
              </div>
              <span className="font-medium text-gray-900 text-sm group-hover:text-blue-700 transition-colors">
                {inst.name}
              </span>
              <span className="text-xs text-gray-400 mt-0.5">
                {inst.city}
                {inst.distance_km != null && ` · ${inst.distance_km} km`}
              </span>
            </Link>
          ))}
        </div>

        {/* Map */}
        <div className="flex-1 relative">
          <InstitutionMap
            institutions={institutions}
            initialViewState={
              userLocation
                ? { longitude: userLocation.lng, latitude: userLocation.lat, zoom: 12 }
                : undefined
            }
          />
        </div>
      </div>
    </div>
  );
}

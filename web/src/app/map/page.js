"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import dynamic from "next/dynamic";
import Link from "next/link";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";

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

const PDOK_SUGGEST = "https://api.pdok.nl/bzk/locatieserver/search/v3_1/suggest";
const PDOK_LOOKUP  = "https://api.pdok.nl/bzk/locatieserver/search/v3_1/lookup";

function AddressSearch({ onLocationSelect }) {
  const [query, setQuery] = useState("");
  const [suggestions, setSuggestions] = useState([]);
  const [open, setOpen] = useState(false);
  const debounce = useRef(null);
  const wrapperRef = useRef(null);

  const fetchSuggestions = useCallback((q) => {
    if (q.length < 3) { setSuggestions([]); setOpen(false); return; }
    fetch(`${PDOK_SUGGEST}?q=${encodeURIComponent(q)}&rows=6&fq=type:(adres+woonplaats+postcode)`)
      .then((r) => r.json())
      .then((data) => {
        const docs = data?.response?.docs || [];
        setSuggestions(docs);
        setOpen(docs.length > 0);
      })
      .catch(() => {});
  }, []);

  const handleInput = (e) => {
    const val = e.target.value;
    setQuery(val);
    clearTimeout(debounce.current);
    debounce.current = setTimeout(() => fetchSuggestions(val), 250);
  };

  const handleSelect = (doc) => {
    setQuery(doc.weergavenaam);
    setOpen(false);
    setSuggestions([]);
    // Lookup exact centroid
    fetch(`${PDOK_LOOKUP}?id=${doc.id}`)
      .then((r) => r.json())
      .then((data) => {
        const centroid = data?.response?.docs?.[0]?.centroide_ll;
        if (centroid?.startsWith("POINT(")) {
          const [lng, lat] = centroid.slice(6, -1).split(" ").map(Number);
          onLocationSelect({ lat, lng, label: doc.weergavenaam });
        }
      })
      .catch(() => {});
  };

  // Close on outside click
  useEffect(() => {
    const handler = (e) => { if (!wrapperRef.current?.contains(e.target)) setOpen(false); };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  return (
    <div ref={wrapperRef} className="relative flex-1 min-w-0 max-w-xs">
      <div className="flex items-center border border-gray-200 rounded-lg bg-white overflow-hidden focus-within:ring-2 focus-within:ring-blue-200 focus-within:border-blue-400">
        <span className="pl-3 text-gray-400 text-sm">🔍</span>
        <input
          type="text"
          value={query}
          onChange={handleInput}
          onFocus={() => suggestions.length > 0 && setOpen(true)}
          placeholder="Zoek adres of stad..."
          className="flex-1 px-2 py-1.5 text-sm text-gray-700 bg-transparent focus:outline-none"
        />
        {query && (
          <button
            onClick={() => { setQuery(""); setSuggestions([]); setOpen(false); }}
            className="pr-3 text-gray-300 hover:text-gray-500"
          >
            ×
          </button>
        )}
      </div>

      {open && (
        <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-gray-100 rounded-xl shadow-lg z-50 overflow-hidden">
          {suggestions.map((doc) => (
            <button
              key={doc.id}
              onMouseDown={() => handleSelect(doc)}
              className="w-full text-left px-4 py-2.5 text-sm text-gray-700 hover:bg-blue-50 transition-colors border-b border-gray-50 last:border-0"
            >
              <span className="font-medium">{doc.weergavenaam}</span>
              {doc.type && (
                <span className="ml-2 text-xs text-gray-400">{doc.type}</span>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export default function MapPage() {
  const { profile } = useAuth();
  const profileRadius = profile?.work_radius_km ?? null;

  const [allInstitutions, setAllInstitutions] = useState([]);
  const [nearbyInstitutions, setNearbyInstitutions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [userLocation, setUserLocation] = useState(null);
  const [filters, setFilters] = useState({ type: "", radius: profileRadius ?? 10 });
  const [mode, setMode] = useState("all");

  // Sync profile radius as default when profile loads (only if user hasn't changed it)
  useEffect(() => {
    if (profileRadius) setFilters((f) => ({ ...f, radius: profileRadius }));
  }, [profileRadius]);

  useEffect(() => {
    setLoading(true);
    api.mapPins()
      .then((data) => setAllInstitutions(Array.isArray(data) ? data : (data.results || [])))
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
      .then(setNearbyInstitutions)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [userLocation, filters]);

  const handleGeolocate = () => {
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setUserLocation({ lat: pos.coords.latitude, lng: pos.coords.longitude });
        setMode("nearby");
      },
      () => alert("Locatie niet beschikbaar. Typ een adres in het zoekveld.")
    );
  };

  const handleAddressSelect = ({ lat, lng }) => {
    setUserLocation({ lat, lng });
    setMode("nearby");
  };

  useEffect(() => {
    if (mode === "nearby" && userLocation) fetchNearby();
  }, [mode, userLocation, filters, fetchNearby]);

  const handleFilterChange = (key, value) => {
    setFilters((f) => ({ ...f, [key]: value }));
  };

  const institutions = mode === "nearby"
    ? nearbyInstitutions
    : (filters.type ? allInstitutions.filter((i) => i.institution_type === filters.type) : allInstitutions);

  return (
    <div className="flex flex-col h-screen bg-white">
      {/* Top bar */}
      <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-100 bg-white z-10 shadow-sm flex-wrap">
        <Link href="/" className="text-lg font-bold text-blue-700 shrink-0">
          KinderopvangBaan
        </Link>

        {/* Address search */}
        <AddressSearch onLocationSelect={handleAddressSelect} />

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

        {/* Radius filter */}
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

        {/* GPS button */}
        <button
          onClick={handleGeolocate}
          title="Gebruik GPS-locatie"
          className="flex items-center gap-1.5 bg-blue-700 text-white text-sm font-medium px-4 py-1.5 rounded-lg hover:bg-blue-800 transition-colors shrink-0"
        >
          📍 Mijn locatie
        </button>

        {mode === "nearby" && (
          <button
            onClick={() => { setMode("all"); setNearbyInstitutions([]); }}
            className="text-sm text-gray-500 hover:text-gray-700 underline shrink-0"
          >
            Alles tonen
          </button>
        )}

        <div className="ml-auto text-sm text-gray-400 shrink-0">
          {loading ? "Laden..." : `${institutions.length} locaties`}
        </div>
      </div>

      {/* Radius filter banner */}
      {mode === "nearby" && (
        <div className="flex items-center gap-3 px-4 py-2 bg-blue-50 border-b border-blue-100 text-sm">
          <span className="text-blue-700">
            📍 Toont resultaten binnen <strong>{filters.radius} km</strong>
            {profileRadius && filters.radius === profileRadius && (
              <span className="ml-1 text-blue-500">(jouw voorkeur)</span>
            )}
          </span>
          <div className="flex items-center gap-1 ml-auto">
            {RADIUS_OPTIONS.map((r) => (
              <button
                key={r}
                onClick={() => handleFilterChange("radius", r)}
                className={`px-2.5 py-0.5 rounded-full text-xs font-medium transition-colors ${
                  filters.radius === r
                    ? "bg-blue-700 text-white"
                    : "bg-white text-blue-600 border border-blue-200 hover:bg-blue-100"
                }`}
              >
                {r} km
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Map + sidebar */}
      <div className="flex flex-1 overflow-hidden">
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

        <div className="flex-1 relative">
          <InstitutionMap
            institutions={institutions}
            center={
              userLocation && mode === "nearby"
                ? { lat: userLocation.lat, lng: userLocation.lng, radius: filters.radius }
                : null
            }
          />
        </div>
      </div>
    </div>
  );
}

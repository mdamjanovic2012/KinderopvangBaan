"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import dynamic from "next/dynamic";
import Link from "next/link";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { getCaoLabel } from "@/lib/caoFunctions";

const JobMap = dynamic(() => import("@/components/JobMap"), {
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center h-full bg-gray-100">
      <div className="text-gray-400 text-sm">Kaart laden...</div>
    </div>
  ),
});

const JOB_TYPE_OPTIONS = [
  { value: "", label: "Alle functies" },
  { value: "pm3", label: "PM KDV" },
  { value: "pm4", label: "PM 3–4 jaar" },
  { value: "bso_begeleider", label: "BSO Begeleider" },
  { value: "locatiemanager", label: "Locatiemanager" },
  { value: "groepshulp", label: "Groepshulp" },
];

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
          <button onClick={() => { setQuery(""); setSuggestions([]); setOpen(false); }} className="pr-3 text-gray-300 hover:text-gray-500">×</button>
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
              {doc.type && <span className="ml-2 text-xs text-gray-400">{doc.type}</span>}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

const RADIUS_OPTIONS = [5, 10, 15, 25, 50];

export default function MapPage() {
  const { user } = useAuth();
  const [jobs, setJobs] = useState([]);
  const [total, setTotal] = useState(0);
  const [blurred, setBlurred] = useState(false);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({ job_type: "", radius: null });
  const [userLocation, setUserLocation] = useState(null);
  const [mobileView, setMobileView] = useState("map");

  useEffect(() => {
    setLoading(true);
    const fetchJobs = userLocation && filters.radius
      ? api.nearbyJobs({ lat: userLocation.lat, lng: userLocation.lng, radius: filters.radius, job_type: filters.job_type || undefined })
      : api.jobMapPins({ job_type: filters.job_type || undefined });

    fetchJobs
      .then((data) => {
        setJobs(data.results || []);
        setTotal(data.total ?? (data.results || []).length);
        setBlurred(data.blurred ?? false);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [filters.job_type, filters.radius, userLocation]);

  const handleGeolocate = () => {
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setUserLocation({ lat: pos.coords.latitude, lng: pos.coords.longitude });
        setFilters((f) => ({ ...f, radius: f.radius ?? 15 }));
      },
      () => alert("Locatie niet beschikbaar. Typ een adres in het zoekveld.")
    );
  };

  return (
    <div className="flex flex-col h-screen bg-white">
      {/* Top bar */}
      <div className="border-b border-gray-100 bg-white z-10 shadow-sm px-4 py-3 space-y-2">
        <div className="flex items-center gap-2">
          <Link href="/" className="text-base sm:text-lg font-bold text-blue-700 shrink-0">
            KinderopvangBaan
          </Link>
          <div className="flex items-center gap-2 ml-auto shrink-0">
            <button
              onClick={handleGeolocate}
              className="flex items-center gap-1.5 bg-blue-700 text-white text-sm font-medium px-3 py-1.5 rounded-lg hover:bg-blue-800 transition-colors"
            >
              📍 <span className="hidden sm:inline">Mijn locatie</span><span className="sm:hidden">Locatie</span>
            </button>
            <span className="text-sm text-gray-400">
              {loading ? "…" : `${total} vacatures`}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <AddressSearch onLocationSelect={(loc) => {
            setUserLocation(loc);
            setFilters((f) => ({ ...f, radius: f.radius ?? 15 }));
          }} />
          <select
            value={filters.job_type}
            onChange={(e) => setFilters((f) => ({ ...f, job_type: e.target.value }))}
            className="flex-1 sm:flex-none border border-gray-200 rounded-lg px-3 py-1.5 text-sm text-gray-700 bg-white focus:outline-none focus:ring-2 focus:ring-blue-200"
          >
            {JOB_TYPE_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </div>

        {/* Radius filter — alleen zichtbaar als locatie bekend is */}
        {userLocation && (
          <div className="flex items-center gap-2 flex-wrap pt-1">
            <span className="text-xs text-gray-500 shrink-0">Straal:</span>
            {RADIUS_OPTIONS.map((r) => (
              <button
                key={r}
                onClick={() => setFilters((f) => ({ ...f, radius: r }))}
                className={`px-2.5 py-0.5 rounded-full text-xs font-medium transition-colors ${
                  filters.radius === r
                    ? "bg-blue-700 text-white"
                    : "bg-gray-100 text-gray-600 hover:bg-blue-100"
                }`}
              >
                {r} km
              </button>
            ))}
            <button
              onClick={() => setFilters((f) => ({ ...f, radius: null }))}
              className={`px-2.5 py-0.5 rounded-full text-xs font-medium transition-colors ${
                filters.radius === null
                  ? "bg-blue-700 text-white"
                  : "bg-gray-100 text-gray-600 hover:bg-blue-100"
              }`}
            >
              Alle
            </button>
          </div>
        )}
      </div>

      {/* Mobile toggle */}
      <div className="sm:hidden flex border-b border-gray-100 bg-white">
        <button
          onClick={() => setMobileView("map")}
          className={`flex-1 py-2.5 text-sm font-medium transition-colors ${mobileView === "map" ? "text-blue-700 border-b-2 border-blue-700" : "text-gray-500"}`}
        >
          🗺️ Kaart
        </button>
        <button
          onClick={() => setMobileView("list")}
          className={`flex-1 py-2.5 text-sm font-medium transition-colors ${mobileView === "list" ? "text-blue-700 border-b-2 border-blue-700" : "text-gray-500"}`}
        >
          📋 Lijst ({jobs.length})
        </button>
      </div>

      {/* Map + sidebar */}
      <div className="flex flex-1 overflow-hidden relative">
        {/* Sidebar list */}
        <div className={`${mobileView === "list" ? "flex" : "hidden"} sm:flex w-full sm:w-80 shrink-0 border-r border-gray-100 bg-white flex-col relative`}>
          {/* Blur overlay voor gasten */}
          {blurred && !user && (
            <div className="absolute inset-0 flex flex-col items-center justify-center z-20">
              <div className="absolute inset-0 bg-white/60 backdrop-blur-sm" />
              <div className="relative z-10 bg-white rounded-2xl shadow-xl px-6 py-5 text-center max-w-xs mx-4">
                <div className="text-2xl mb-2">📋</div>
                <h2 className="text-base font-bold text-gray-900 mb-1">
                  Bekijk alle {total} vacatures
                </h2>
                <p className="text-xs text-gray-500 mb-4">
                  Registreer gratis en zie alle vacatures in de lijst.
                </p>
                <Link
                  href="/register"
                  className="block w-full bg-blue-700 text-white text-xs font-semibold px-4 py-2 rounded-xl hover:bg-blue-800 transition-colors text-center"
                >
                  Gratis registreren →
                </Link>
                <Link
                  href="/login"
                  className="block mt-2 text-xs text-gray-400 hover:text-gray-600 underline"
                >
                  Al een account? Inloggen
                </Link>
              </div>
            </div>
          )}
          <div className="overflow-y-auto flex-1">
            {jobs.length === 0 && !loading && (
              <div className="p-6 text-center text-gray-400 text-sm">Geen vacatures gevonden.</div>
            )}
            {jobs.map((job) => (
              <Link
                key={job.id}
                href={`/jobs/${job.id}`}
                className="flex flex-col p-4 border-b border-gray-50 hover:bg-blue-50 transition-colors cursor-pointer group"
              >
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-blue-50 text-blue-700">
                    {getCaoLabel(job.job_type) || job.job_type}
                  </span>
                </div>
                <span className="font-medium text-gray-900 text-sm group-hover:text-blue-700 transition-colors">
                  {job.title}
                </span>
                <span className="text-xs text-gray-400 mt-0.5">
                  {job.company_name} · {job.city}
                </span>
              </Link>
            ))}
          </div>
        </div>

        {/* Map */}
        <div className={`${mobileView === "map" ? "flex" : "hidden"} sm:flex flex-1 relative`}>
          <JobMap
            jobs={jobs}
            center={userLocation}
          />

          {/* Blur overlay voor gasten */}
          {blurred && !user && (
            <div className="absolute inset-0 flex flex-col items-center justify-center z-20">
              <div className="absolute inset-0 bg-white/60 backdrop-blur-sm" />
              <div className="relative z-10 bg-white rounded-2xl shadow-xl px-8 py-6 text-center max-w-sm mx-4">
                <div className="text-3xl mb-3">🗺️</div>
                <h2 className="text-lg font-bold text-gray-900 mb-1">
                  Bekijk alle {total} vacatures op de kaart
                </h2>
                <p className="text-sm text-gray-500 mb-5">
                  Registreer gratis en zie alle vacatures dicht bij jou in de buurt.
                </p>
                <Link
                  href="/register"
                  className="block w-full bg-blue-700 text-white text-sm font-semibold px-6 py-2.5 rounded-xl hover:bg-blue-800 transition-colors text-center"
                >
                  Gratis registreren →
                </Link>
                <Link
                  href="/login"
                  className="block mt-2 text-xs text-gray-400 hover:text-gray-600 underline"
                >
                  Al een account? Inloggen
                </Link>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

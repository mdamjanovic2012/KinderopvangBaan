"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import Nav from "@/components/Nav";
import { useAuth } from "@/context/AuthContext";
import { CAO_FUNCTIONS, getCaoLabel } from "@/lib/caoFunctions";

const JOB_TYPE_OPTIONS = [
  { value: "", label: "Alle functies" },
  ...CAO_FUNCTIONS,
];

const CONTRACT_OPTIONS = [
  { value: "", label: "Alle contracten" },
  { value: "fulltime", label: "Full-time" },
  { value: "parttime", label: "Part-time" },
  { value: "temp", label: "Tijdelijk" },
];

const RADIUS_OPTIONS = [5, 10, 15, 20];

const CONTRACT_COLORS = {
  fulltime: "bg-blue-50 text-blue-600",
  parttime: "bg-emerald-50 text-emerald-600",
  temp: "bg-purple-50 text-purple-600",
};

const CONTRACT_LABELS = {
  fulltime: "Full-time",
  parttime: "Part-time",
  temp: "Tijdelijk",
};

function JobCard({ job }) {
  const daysAgo = Math.floor(
    (new Date() - new Date(job.created_at)) / (1000 * 60 * 60 * 24)
  );

  return (
    <Link
      href={`/jobs/${job.id}`}
      className="block bg-white rounded-2xl p-5 border border-gray-100 shadow-sm hover:border-blue-200 hover:shadow-md transition-all group"
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-2 flex-wrap">
            <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${CONTRACT_COLORS[job.contract_type] || "bg-gray-100 text-gray-600"}`}>
              {CONTRACT_LABELS[job.contract_type] || job.contract_type}
            </span>
            {job.is_premium && (
              <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-yellow-50 text-yellow-600">
                Uitgelicht
              </span>
            )}
            {job.requires_vog && (
              <span className="text-xs text-gray-400">VOG vereist</span>
            )}
          </div>

          <h3 className="font-semibold text-gray-900 group-hover:text-blue-700 transition-colors mb-0.5">
            {job.title}
          </h3>

          <div className="text-sm text-gray-500 mb-3">
            <span className="font-medium text-gray-700">{job.institution_name}</span>
            {" · "}
            {job.institution_city || job.city}
            {job.distance_km != null && (
              <span className="text-blue-600 font-medium"> · {job.distance_km} km</span>
            )}
          </div>

          {job.description && (
            <p className="text-sm text-gray-400 line-clamp-2 leading-relaxed">
              {job.description}
            </p>
          )}
        </div>

        <div className="shrink-0 text-right">
          {(job.salary_min || job.salary_max) && (
            <div className="text-sm font-semibold text-gray-900 mb-1">
              €{job.salary_min}
              {job.salary_max && job.salary_max !== job.salary_min && `–${job.salary_max}`}
              <span className="text-xs font-normal text-gray-400">/u</span>
            </div>
          )}
          {job.hours_per_week && (
            <div className="text-xs text-gray-400">{job.hours_per_week} uur/week</div>
          )}
          <div className="text-xs text-gray-300 mt-2">
            {daysAgo === 0 ? "Vandaag" : daysAgo === 1 ? "Gisteren" : `${daysAgo}d geleden`}
          </div>
        </div>
      </div>
    </Link>
  );
}

const PDOK_URL = "https://api.pdok.nl/bzk/locatieserver/search/v3_1/free";

async function lookupPostcode(postcode) {
  const cleaned = postcode.replace(/\s/g, "").toUpperCase();
  if (!/^\d{4}[A-Z]{2}$/.test(cleaned)) return null;
  try {
    const res = await fetch(`${PDOK_URL}?q=${cleaned}&fq=type:postcode6&rows=1&fl=centroide_ll`);
    const json = await res.json();
    const doc = json?.response?.docs?.[0];
    if (!doc?.centroide_ll) return null;
    // centroide_ll = "POINT(lon lat)"
    const match = doc.centroide_ll.match(/POINT\(([\d.]+)\s+([\d.]+)\)/);
    if (!match) return null;
    return { lng: parseFloat(match[1]), lat: parseFloat(match[2]) };
  } catch {
    return null;
  }
}

export default function JobsPage() {
  const { profile } = useAuth();
  const profileRadius = profile?.work_radius_km ?? null;

  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState("");
  const [filters, setFilters] = useState({ job_type: "", contract_type: "", radius: profileRadius ?? 15 });
  const [mode, setMode] = useState("all");
  const [userLocation, setUserLocation] = useState(null);

  useEffect(() => {
    if (profileRadius) setFilters((f) => ({ ...f, radius: profileRadius }));
  }, [profileRadius]);

  // Auto-fill locatie vanuit profiel postcode als ingelogd
  useEffect(() => {
    if (profile?.postcode && !userLocation) {
      lookupPostcode(profile.postcode).then((loc) => {
        if (loc) {
          setUserLocation(loc);
          setMode("nearby");
        }
      });
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [profile?.postcode]);

  const loadAll = useCallback(() => {
    setLoading(true);
    const params = {};
    if (filters.job_type) params.job_type = filters.job_type;
    if (filters.contract_type) params.contract_type = filters.contract_type;
    if (search) params.search = search;
    api.jobs(params)
      .then((data) => setJobs(data.results || data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [filters, search]);

  const loadNearby = useCallback(() => {
    if (!userLocation) return;
    setLoading(true);
    api.nearbyJobs({
      lat: userLocation.lat,
      lng: userLocation.lng,
      radius: filters.radius,
      type: filters.job_type || undefined,
    })
      .then(setJobs)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [userLocation, filters]);

  useEffect(() => {
    if (mode === "all") loadAll();
    else loadNearby();
  }, [mode, loadAll, loadNearby]);

  const handleGeolocate = () => {
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setUserLocation({ lat: pos.coords.latitude, lng: pos.coords.longitude });
        setMode("nearby");
      },
      () => alert("Locatie niet beschikbaar.")
    );
  };

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    if (mode === "all") loadAll();
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <Nav />

      {/* Filter bar */}
      <div className="bg-white border-b border-gray-100 shadow-sm">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 py-4 flex items-center gap-2 sm:gap-3 flex-wrap">
          {/* Search */}
          <form onSubmit={handleSearchSubmit} className="w-full sm:flex-1 sm:min-w-48">
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Zoek vacatures, functies, steden..."
              className="w-full border border-gray-200 rounded-lg px-3 py-1.5 text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-200"
            />
          </form>

          <select
            value={filters.job_type}
            onChange={(e) => setFilters((f) => ({ ...f, job_type: e.target.value }))}
            className="flex-1 sm:flex-none border border-gray-200 rounded-lg px-3 py-1.5 text-sm text-gray-700 bg-white focus:outline-none focus:ring-2 focus:ring-blue-200"
          >
            {JOB_TYPE_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>

          <select
            value={filters.contract_type}
            onChange={(e) => setFilters((f) => ({ ...f, contract_type: e.target.value }))}
            className="flex-1 sm:flex-none border border-gray-200 rounded-lg px-3 py-1.5 text-sm text-gray-700 bg-white focus:outline-none focus:ring-2 focus:ring-blue-200"
          >
            {CONTRACT_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>

          <button
            onClick={handleGeolocate}
            className="flex items-center gap-1.5 bg-blue-700 text-white text-sm font-medium px-4 py-1.5 rounded-lg hover:bg-blue-800 transition-colors shrink-0"
          >
            📍 In mijn buurt
          </button>

          {mode === "nearby" && (
            <button
              onClick={() => setMode("all")}
              className="text-sm text-gray-500 hover:text-gray-700 underline"
            >
              Alles tonen
            </button>
          )}
        </div>
      </div>

      {/* Radius banner */}
      {mode === "nearby" && (
        <div className="bg-blue-50 border-b border-blue-100">
          <div className="max-w-5xl mx-auto px-6 py-2 flex items-center gap-3 flex-wrap">
            <span className="text-sm text-blue-700">
              📍 Vacatures binnen <strong>{filters.radius} km</strong>
              {profileRadius && filters.radius === profileRadius && (
                <span className="ml-1 text-blue-500">(jouw voorkeur)</span>
              )}
            </span>
            <div className="flex items-center gap-1 ml-auto">
              {RADIUS_OPTIONS.map((r) => (
                <button
                  key={r}
                  onClick={() => setFilters((f) => ({ ...f, radius: r }))}
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
        </div>
      )}

      <div className="max-w-5xl mx-auto px-4 sm:px-6 py-6 sm:py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-xl font-bold text-gray-900">Vacatures kinderopvang</h1>
            <p className="text-sm text-gray-400 mt-0.5">
              {loading ? "Laden..." : `${jobs.length} vacatures gevonden`}
              {mode === "nearby" && userLocation && ` binnen ${filters.radius} km`}
            </p>
          </div>
          <Link
            href="/map"
            className="text-sm text-blue-700 hover:underline"
          >
            Bekijk kaart →
          </Link>
        </div>

        {/* Jobs list */}
        {!loading && jobs.length === 0 && (
          <div className="text-center py-20 text-gray-400">
            <div className="text-4xl mb-3">🔍</div>
            <p className="text-sm">Geen vacatures gevonden.</p>
            <p className="text-xs mt-1">Pas de filters aan of vergroot de zoekradius.</p>
          </div>
        )}

        <div className="space-y-3">
          {jobs.map((job) => (
            <JobCard key={job.id} job={job} />
          ))}
        </div>
      </div>
    </div>
  );
}

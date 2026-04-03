"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import Nav from "@/components/Nav";
import { useAuth } from "@/context/AuthContext";
import { CAO_FUNCTIONS } from "@/lib/caoFunctions";

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

const HOURS_OPTIONS = [
  { label: "Alle uren", hours_min: "", hours_max: "" },
  { label: "≤ 24 uur", hours_min: "", hours_max: "24" },
  { label: "24–32 uur", hours_min: "24", hours_max: "32" },
  { label: "≥ 32 uur", hours_min: "32", hours_max: "" },
];

const RADIUS_OPTIONS = [5, 10, 15, 20];

const CONTRACT_COLORS = {
  fulltime: "bg-blue-50 text-blue-600",
  parttime: "bg-orange-50 text-orange-600",
  temp: "bg-purple-50 text-purple-600",
};

const CONTRACT_LABELS = {
  fulltime: "Full-time",
  parttime: "Part-time",
  temp: "Tijdelijk",
};

function JobCard({ job, blurred = false }) {
  const daysAgo = Math.floor(
    (new Date() - new Date(job.created_at)) / (1000 * 60 * 60 * 24)
  );
  const dateLabel = daysAgo === 0 ? "Vandaag geplaatst" : daysAgo === 1 ? "Gisteren geplaatst" : `${daysAgo} dagen geleden`;
  const isGoodMatch = job.distance_km != null && job.distance_km <= 5;
  const hoursLabel = job.hours_min && job.hours_max && job.hours_min !== job.hours_max
    ? `${job.hours_min}–${job.hours_max} uur`
    : job.hours_min || job.hours_max
      ? `${job.hours_min || job.hours_max} uur`
      : null;

  return (
    <Link
      href={blurred ? "/register" : `/jobs/${job.id}`}
      className={`block bg-white rounded-2xl border border-gray-100 shadow-sm transition-all group relative overflow-hidden ${
        blurred
          ? "blur-sm pointer-events-none select-none"
          : "hover:border-blue-200 hover:shadow-md"
      }`}
      tabIndex={blurred ? -1 : undefined}
      aria-hidden={blurred}
    >
      {job.is_premium && (
        <div className="absolute top-0 left-0 right-0 h-0.5 bg-gradient-to-r from-yellow-400 to-amber-500" />
      )}

      <div className="flex flex-col sm:flex-row sm:items-stretch">
        {/* Left: main content */}
        <div className="flex-1 min-w-0 p-5">
          <div className="flex items-start gap-3">
            {/* Logo */}
            {job.company_logo ? (
              <img
                src={job.company_logo}
                alt={job.company_name}
                className="w-14 h-14 rounded-full object-contain border border-gray-200 shrink-0 bg-white p-1"
              />
            ) : (
              <div className="w-14 h-14 rounded-full bg-blue-50 border border-gray-200 flex items-center justify-center shrink-0 text-blue-600 font-bold text-xl">
                {job.company_name?.[0] ?? "?"}
              </div>
            )}

            <div className="flex-1 min-w-0">
              {/* Title */}
              <h3 className="font-bold text-gray-900 group-hover:text-blue-700 transition-colors leading-snug mb-2">
                {job.title}
              </h3>

              {/* Location row — pin + city + distance + hours badge */}
              <div className="flex items-center gap-2 flex-wrap text-sm text-gray-500 mb-1.5">
                <svg className="w-3.5 h-3.5 text-gray-400 shrink-0" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                  <path strokeLinecap="round" strokeLinejoin="round" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
                <span>{job.city || job.location_name || "–"}</span>
                {job.distance_km != null && (
                  <span className="text-gray-400">· {job.distance_km} km van jou</span>
                )}
                {hoursLabel && (
                  <span className="px-2.5 py-0.5 rounded-full bg-blue-600 text-white text-xs font-semibold">
                    {hoursLabel}
                  </span>
                )}
              </div>

              {/* Hours per week */}
              {hoursLabel && (
                <div className="flex items-center gap-1.5 text-sm text-gray-500 mb-1.5">
                  <svg className="w-3.5 h-3.5 text-gray-400 shrink-0" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                    <circle cx="12" cy="12" r="10"/><path strokeLinecap="round" d="M12 6v6l4 2"/>
                  </svg>
                  {hoursLabel} per week
                </div>
              )}

              {/* Date */}
              <div className="flex items-center gap-1.5 text-sm text-gray-500 mb-3">
                <svg className="w-3.5 h-3.5 text-gray-400 shrink-0" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                  <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>
                </svg>
                {dateLabel}
              </div>

              {/* Company name */}
              <div className="text-sm font-bold text-gray-900 mb-1">{job.company_name}</div>

              {/* Short description */}
              {job.short_description && (
                <p className="text-sm text-gray-400 line-clamp-1 leading-relaxed">
                  {job.short_description}
                </p>
              )}
            </div>
          </div>
        </div>

        {/* Divider */}
        <div className="hidden sm:block w-px bg-gray-100 my-4" />

        {/* Right: salary + badges */}
        <div className="sm:w-44 shrink-0 px-5 pb-5 sm:py-5 sm:pl-0 flex flex-row sm:flex-col items-center sm:items-end justify-between sm:justify-center gap-3">
          <div className="text-right">
            {(job.salary_min || job.salary_max) ? (
              <>
                <div className="text-base font-bold text-gray-900">
                  €{Math.round(job.salary_min).toLocaleString("nl-NL")}
                  {job.salary_max && Number(job.salary_max) !== Number(job.salary_min) && (
                    <> – €{Math.round(job.salary_max).toLocaleString("nl-NL")}</>
                  )}
                </div>
                <div className="text-xs text-gray-400">per maand</div>
              </>
            ) : (
              <div className="text-xs text-gray-300 italic">salaris n.o.t.k.</div>
            )}
          </div>

          <div className="flex flex-col items-end gap-1.5">
            {job.contract_type && (
              <span className={`text-xs font-semibold px-2.5 py-1 rounded-full ${CONTRACT_COLORS[job.contract_type] || "bg-gray-100 text-gray-600"}`}>
                {CONTRACT_LABELS[job.contract_type] || job.contract_type}
              </span>
            )}
            {job.is_premium && (
              <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-yellow-50 text-yellow-600">
                ★ Uitgelicht
              </span>
            )}
            {isGoodMatch && (
              <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-amber-50 text-amber-600 flex items-center gap-1 whitespace-nowrap">
                ⭐ Goede match
              </span>
            )}
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
    const match = doc.centroide_ll.match(/POINT\(([\d.]+)\s+([\d.]+)\)/);
    if (!match) return null;
    return { lng: parseFloat(match[1]), lat: parseFloat(match[2]) };
  } catch {
    return null;
  }
}

const EMPTY_FILTERS = {
  job_type: "",
  contract_type: "",
  radius: 15,
  city: "",
  hours_min: "",
  hours_max: "",
  requires_diploma: "",
};

export default function JobsPage() {
  const { user, profile } = useAuth();
  const profileRadius = profile?.work_radius_km ?? null;

  const [jobs, setJobs] = useState([]);
  const [total, setTotal] = useState(0);
  const [blurred, setBlurred] = useState(false);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState("");
  const [filters, setFilters] = useState({ ...EMPTY_FILTERS, radius: profileRadius ?? 15 });
  const [mode, setMode] = useState("all");
  const [userLocation, setUserLocation] = useState(null);
  const [advancedOpen, setAdvancedOpen] = useState(false);

  useEffect(() => {
    if (profileRadius) setFilters((f) => ({ ...f, radius: profileRadius }));
  }, [profileRadius]);

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

  const buildParams = useCallback(() => {
    const p = {};
    if (filters.job_type) p.job_type = filters.job_type;
    if (filters.contract_type) p.contract_type = filters.contract_type;
    if (filters.city) p.city = filters.city;
    if (filters.hours_min) p.hours_min = filters.hours_min;
    if (filters.hours_max) p.hours_max = filters.hours_max;
    if (filters.requires_diploma !== "") p.requires_diploma = filters.requires_diploma;
    if (search) p.search = search;
    return p;
  }, [filters, search]);

  const loadAll = useCallback(() => {
    setLoading(true);
    api.jobs(buildParams())
      .then((data) => {
        setJobs(data.results || []);
        setTotal(data.total ?? (data.results || []).length);
        setBlurred(data.blurred ?? false);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [buildParams]);

  const loadNearby = useCallback(() => {
    if (!userLocation) return;
    setLoading(true);
    api.nearbyJobs({
      lat: userLocation.lat,
      lng: userLocation.lng,
      radius: filters.radius,
      ...buildParams(),
    })
      .then((data) => {
        setJobs(data.results || []);
        setTotal(data.total ?? (data.results || []).length);
        setBlurred(data.blurred ?? false);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [userLocation, filters.radius, buildParams]);

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

  const setHours = (opt) => {
    setFilters((f) => ({ ...f, hours_min: opt.hours_min, hours_max: opt.hours_max }));
  };

  const activeHoursOption = HOURS_OPTIONS.find(
    (o) => o.hours_min === filters.hours_min && o.hours_max === filters.hours_max
  ) ?? HOURS_OPTIONS[0];

  const advancedCount = [
    filters.city,
    filters.hours_min || filters.hours_max,
    filters.requires_diploma,
  ].filter(Boolean).length;

  const hiddenCount = total - jobs.length;

  return (
    <div className="min-h-screen bg-gray-50">
      <Nav />

      {/* Filter bar */}
      <div className="bg-white border-b border-gray-100 shadow-sm">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 py-4 flex items-center gap-2 sm:gap-3 flex-wrap">
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
            onClick={() => setAdvancedOpen((o) => !o)}
            className={`relative flex items-center gap-1.5 text-sm font-medium px-3 py-1.5 rounded-lg border transition-colors ${
              advancedOpen || advancedCount > 0
                ? "bg-blue-50 border-blue-200 text-blue-700"
                : "bg-white border-gray-200 text-gray-600 hover:border-blue-200"
            }`}
          >
            Geavanceerd {advancedOpen ? "▴" : "▾"}
            {advancedCount > 0 && (
              <span className="absolute -top-1.5 -right-1.5 w-4 h-4 rounded-full bg-blue-600 text-white text-[10px] font-bold flex items-center justify-center">
                {advancedCount}
              </span>
            )}
          </button>

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

        {/* Advanced filter panel */}
        {advancedOpen && (
          <div className="border-t border-gray-100 bg-gray-50">
            <div className="max-w-5xl mx-auto px-4 sm:px-6 py-4 flex flex-wrap gap-6">
              {/* City */}
              <div className="flex flex-col gap-1.5 min-w-40">
                <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Stad</label>
                <input
                  type="text"
                  value={filters.city}
                  onChange={(e) => setFilters((f) => ({ ...f, city: e.target.value }))}
                  placeholder="bijv. Amsterdam"
                  className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm text-gray-700 bg-white focus:outline-none focus:ring-2 focus:ring-blue-200"
                />
              </div>

              {/* Hours */}
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Uren per week</label>
                <div className="flex gap-1.5 flex-wrap">
                  {HOURS_OPTIONS.map((opt) => (
                    <button
                      key={opt.label}
                      onClick={() => setHours(opt)}
                      className={`px-3 py-1.5 rounded-lg text-sm font-medium border transition-colors ${
                        activeHoursOption.label === opt.label
                          ? "bg-blue-700 text-white border-blue-700"
                          : "bg-white text-gray-600 border-gray-200 hover:border-blue-300"
                      }`}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Diploma */}
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Diploma vereist</label>
                <div className="flex gap-1.5">
                  {[{ label: "Alle", value: "" }, { label: "Ja", value: "true" }, { label: "Nee", value: "false" }].map((opt) => (
                    <button
                      key={opt.label}
                      onClick={() => setFilters((f) => ({ ...f, requires_diploma: opt.value }))}
                      className={`px-3 py-1.5 rounded-lg text-sm font-medium border transition-colors ${
                        filters.requires_diploma === opt.value
                          ? "bg-blue-700 text-white border-blue-700"
                          : "bg-white text-gray-600 border-gray-200 hover:border-blue-300"
                      }`}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Reset */}
              {advancedCount > 0 && (
                <div className="flex items-end">
                  <button
                    onClick={() => setFilters((f) => ({ ...f, city: "", hours_min: "", hours_max: "", requires_diploma: "" }))}
                    className="text-sm text-gray-400 hover:text-red-500 transition-colors underline"
                  >
                    Wis filters
                  </button>
                </div>
              )}
            </div>
          </div>
        )}
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
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-xl font-bold text-gray-900">Vacatures kinderopvang</h1>
            <p className="text-sm text-gray-400 mt-0.5">
              {loading ? "Laden..." : `${total} vacatures gevonden`}
              {mode === "nearby" && userLocation && ` binnen ${filters.radius} km`}
            </p>
          </div>
          <Link href="/map" className="text-sm text-blue-700 hover:underline">
            Bekijk kaart →
          </Link>
        </div>

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

        {/* Blur CTA voor gasten */}
        {blurred && !user && hiddenCount > 0 && (
          <div className="relative mt-3">
            <div className="space-y-3 pointer-events-none select-none">
              {Array.from({ length: Math.min(hiddenCount, 3) }).map((_, i) => (
                <div key={i} className="bg-white rounded-2xl p-5 border border-gray-100 shadow-sm blur-sm h-24" />
              ))}
            </div>

            <div className="absolute inset-0 flex flex-col items-center justify-center bg-gradient-to-t from-gray-50 via-gray-50/80 to-transparent rounded-2xl px-4 py-8">
              <p className="text-sm font-semibold text-gray-800 mb-1">
                Nog <strong>{hiddenCount}</strong> vacatures verborgen
              </p>
              <p className="text-xs text-gray-500 mb-4 text-center">
                Registreer gratis in 1 minuut en bekijk alle vacatures
              </p>
              <Link
                href="/register"
                className="bg-blue-700 text-white text-sm font-semibold px-6 py-2.5 rounded-xl hover:bg-blue-800 transition-colors"
              >
                Gratis registreren →
              </Link>
              <Link href="/login" className="mt-2 text-xs text-gray-400 hover:text-gray-600 underline">
                Al een account? Inloggen
              </Link>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

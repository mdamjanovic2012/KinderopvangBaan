"use client";

import { useState, useEffect, useRef } from "react";
import Link from "next/link";
import Nav from "@/components/Nav";
import { api } from "@/lib/api";

const LEVEL_COLORS = {
  mbo2: "bg-gray-100 text-gray-600",
  mbo3: "bg-blue-50 text-blue-600",
  mbo4: "bg-blue-100 text-blue-700",
  hbo: "bg-purple-50 text-purple-700",
  wo: "bg-purple-100 text-purple-800",
};

const STATUS_CONFIG = {
  direct: {
    color: "bg-green-50 border-green-200",
    badge: "bg-green-100 text-green-700",
    icon: (
      <svg className="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
      </svg>
    ),
    label: "Direct bevoegd",
    desc: "Je kwalificeert direct voor deze opvangvorm.",
  },
  proof_required: {
    color: "bg-amber-50 border-amber-200",
    badge: "bg-amber-100 text-amber-700",
    icon: (
      <svg className="w-5 h-5 text-amber-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
      </svg>
    ),
    label: "Bevoegd met aanvullend bewijs",
    desc: "Je kwalificeert mits je aanvullend bewijs van pedagogische competenties overlegt.",
  },
  not_qualified: {
    color: "bg-red-50 border-red-200",
    badge: "bg-red-100 text-red-600",
    icon: (
      <svg className="w-5 h-5 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
      </svg>
    ),
    label: "Niet bevoegd",
    desc: "Dit diploma kwalificeert niet voor deze opvangvorm.",
  },
};

function buildRegisterUrl(selected) {
  const opvangtypes = [];
  if (selected.kdv_status !== "not_qualified") opvangtypes.push("kdv");
  if (selected.bso_status !== "not_qualified") opvangtypes.push("bso");
  const params = new URLSearchParams();
  if (opvangtypes.length) params.set("opvangtype", opvangtypes.join(","));
  if (selected.kdv_status === "proof_required") params.set("kdv_proof", "1");
  if (selected.bso_status === "proof_required") params.set("bso_proof", "1");
  return `/register?${params.toString()}`;
}

export default function DiplomaCheckPage() {
  const [query, setQuery] = useState("");
  const [suggestions, setSuggestions] = useState([]);
  const [selected, setSelected] = useState(null);
  const [loading, setLoading] = useState(false);
  const [showDropdown, setShowDropdown] = useState(false);
  const debounceRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    if (query.length < 2) {
      setSuggestions([]);
      setShowDropdown(false);
      return;
    }
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(async () => {
      setLoading(true);
      try {
        const data = await api.get(`/diplomacheck/search/?q=${encodeURIComponent(query)}`);
        setSuggestions(data);
        setShowDropdown(true);
      } catch {
        setSuggestions([]);
      } finally {
        setLoading(false);
      }
    }, 300);
  }, [query]);

  const handleSelect = async (diploma) => {
    setShowDropdown(false);
    setQuery(diploma.name);
    setLoading(true);
    try {
      const data = await api.get(`/diplomacheck/${diploma.id}/`);
      setSelected(data);
    } catch {
      setSelected(null);
    } finally {
      setLoading(false);
    }
  };

  const handleClear = () => {
    setQuery("");
    setSelected(null);
    setSuggestions([]);
    inputRef.current?.focus();
  };

  const qualifiesAnywhere =
    selected &&
    (selected.kdv_status !== "not_qualified" || selected.bso_status !== "not_qualified");

  return (
    <>
      <Nav />
      <main className="min-h-screen bg-gray-50">
        {/* Header */}
        <div className="bg-white border-b border-gray-100">
          <div className="max-w-2xl mx-auto px-4 py-10 text-center">
            <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-blue-50 mb-4">
              <svg className="w-7 h-7 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M9 12l2 2 4-4M7.835 4.697a3.42 3.42 0 001.946-.806 3.42 3.42 0 014.438 0 3.42 3.42 0 001.946.806 3.42 3.42 0 013.138 3.138 3.42 3.42 0 00.806 1.946 3.42 3.42 0 010 4.438 3.42 3.42 0 00-.806 1.946 3.42 3.42 0 01-3.138 3.138 3.42 3.42 0 00-1.946.806 3.42 3.42 0 01-4.438 0 3.42 3.42 0 00-1.946-.806 3.42 3.42 0 01-3.138-3.138 3.42 3.42 0 00-.806-1.946 3.42 3.42 0 010-4.438 3.42 3.42 0 00.806-1.946 3.42 3.42 0 013.138-3.138z" />
              </svg>
            </div>
            <h1 className="text-2xl font-bold text-gray-900 mb-2">Diplomacheck kinderopvang</h1>
            <p className="text-gray-500 text-sm max-w-md mx-auto">
              Zoek je diploma en ontdek direct voor welke opvangvormen jij kwalificeert.
            </p>
          </div>
        </div>

        <div className="max-w-2xl mx-auto px-4 py-8 space-y-6">
          {/* Zoekveld */}
          <div className="relative">
            <div className="relative">
              <div className="absolute inset-y-0 left-4 flex items-center pointer-events-none">
                {loading ? (
                  <svg className="w-5 h-5 text-blue-400 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                  </svg>
                ) : (
                  <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                  </svg>
                )}
              </div>
              <input
                ref={inputRef}
                type="text"
                value={query}
                onChange={(e) => { setQuery(e.target.value); setSelected(null); }}
                onFocus={() => suggestions.length > 0 && setShowDropdown(true)}
                placeholder="Zoek op diplomanaam of CREBO-nummer..."
                className="w-full pl-12 pr-10 py-3.5 border border-gray-200 rounded-xl bg-white shadow-sm text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
              {query && (
                <button
                  onClick={handleClear}
                  className="absolute inset-y-0 right-3 flex items-center text-gray-300 hover:text-gray-500"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              )}
            </div>

            {/* Autocomplete dropdown */}
            {showDropdown && suggestions.length > 0 && (
              <div className="absolute z-10 w-full mt-1 bg-white border border-gray-100 rounded-xl shadow-lg overflow-hidden">
                {suggestions.map((d) => (
                  <button
                    key={d.id}
                    onClick={() => handleSelect(d)}
                    className="w-full text-left px-4 py-3 hover:bg-blue-50 transition-colors flex items-center justify-between gap-3 border-b border-gray-50 last:border-0"
                  >
                    <div>
                      <p className="text-sm font-medium text-gray-900">{d.name}</p>
                      {d.crebo && <p className="text-xs text-gray-400">CREBO {d.crebo}</p>}
                    </div>
                    <span className={`shrink-0 text-xs font-medium px-2 py-0.5 rounded-full ${LEVEL_COLORS[d.level] || "bg-gray-100 text-gray-600"}`}>
                      {d.level_display}
                    </span>
                  </button>
                ))}
              </div>
            )}

            {showDropdown && suggestions.length === 0 && query.length >= 2 && !loading && (
              <div className="absolute z-10 w-full mt-1 bg-white border border-gray-100 rounded-xl shadow-lg px-4 py-3 text-sm text-gray-400">
                Geen diploma gevonden voor &ldquo;{query}&rdquo;
              </div>
            )}
          </div>

          {/* Resultaat */}
          {selected && (
            <div className="space-y-4">
              {/* Diploma header */}
              <div className="bg-white rounded-xl border border-gray-100 shadow-sm px-6 py-4 flex items-start justify-between gap-3">
                <div>
                  <h2 className="text-base font-semibold text-gray-900">{selected.name}</h2>
                  {selected.crebo && (
                    <p className="text-sm text-gray-400 mt-0.5">CREBO {selected.crebo}</p>
                  )}
                </div>
                <span className={`shrink-0 text-xs font-medium px-3 py-1 rounded-full ${LEVEL_COLORS[selected.level] || "bg-gray-100 text-gray-600"}`}>
                  {selected.level_display}
                </span>
              </div>

              {/* KDV + BSO status cards */}
              <div className="grid grid-cols-2 gap-3">
                {[
                  { key: "kdv_status", title: "KDV", subtitle: "Kinderdagverblijf · Dagopvang" },
                  { key: "bso_status", title: "BSO", subtitle: "Buitenschoolse opvang" },
                ].map(({ key, title, subtitle }) => {
                  const status = selected[key] || "not_qualified";
                  const cfg = STATUS_CONFIG[status];
                  return (
                    <div key={key} className={`rounded-xl border p-4 ${cfg.color}`}>
                      <div className="flex items-center gap-2 mb-2">
                        {cfg.icon}
                        <span className="font-semibold text-gray-900 text-sm">{title}</span>
                      </div>
                      <p className="text-xs text-gray-500 mb-2">{subtitle}</p>
                      <span className={`inline-block text-xs font-medium px-2 py-0.5 rounded-full ${cfg.badge}`}>
                        {cfg.label}
                      </span>
                    </div>
                  );
                })}
              </div>

              {/* Aanvullende info */}
              {selected.notes && (
                <div className="bg-amber-50 border border-amber-100 rounded-xl px-4 py-3 text-sm text-gray-600">
                  {selected.notes}
                </div>
              )}

              {/* CTA */}
              {qualifiesAnywhere ? (
                <div className="bg-blue-700 rounded-xl p-5 text-white">
                  <h3 className="font-semibold text-base mb-1">Vind vacatures die bij jou passen</h3>
                  <p className="text-blue-100 text-sm mb-4">
                    Maak een gratis profiel aan en zie direct welke banen jij kunt solliciteren.
                  </p>
                  <Link
                    href={buildRegisterUrl(selected)}
                    className="inline-block bg-white text-blue-700 font-semibold px-5 py-2.5 rounded-lg hover:bg-blue-50 transition-colors text-sm"
                  >
                    Gratis profiel aanmaken →
                  </Link>
                </div>
              ) : (
                <div className="bg-gray-100 rounded-xl p-5 text-center">
                  <p className="text-sm text-gray-500 mb-3">
                    Dit diploma kwalificeert niet direct voor KDV of BSO. Bekijk de vacatures of neem contact op met een instelling voor meer informatie.
                  </p>
                  <Link href="/jobs" className="text-sm text-blue-700 hover:underline font-medium">
                    Bekijk alle vacatures →
                  </Link>
                </div>
              )}
            </div>
          )}

          {/* Lege staat */}
          {!selected && query.length < 2 && (
            <div className="text-center py-8 text-gray-400 text-sm">
              <p>Typ minimaal 2 tekens om te zoeken</p>
              <p className="mt-1 text-xs">Bijv. &ldquo;pedagogisch&rdquo;, &ldquo;social work&rdquo; of een CREBO-nummer</p>
            </div>
          )}
        </div>
      </main>
    </>
  );
}

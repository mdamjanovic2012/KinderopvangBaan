"use client";

import { useState, useEffect, useRef } from "react";
import Link from "next/link";
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
    border: "border-green-200 bg-green-50",
    badge: "bg-green-100 text-green-700",
    icon: (
      <svg className="w-4 h-4 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
      </svg>
    ),
    label: "Direct bevoegd",
  },
  proof_required: {
    border: "border-amber-200 bg-amber-50",
    badge: "bg-amber-100 text-amber-700",
    icon: (
      <svg className="w-4 h-4 text-amber-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
      </svg>
    ),
    label: "Met aanvullend bewijs",
  },
  not_qualified: {
    border: "border-red-100 bg-red-50",
    badge: "bg-red-100 text-red-600",
    icon: (
      <svg className="w-4 h-4 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
      </svg>
    ),
    label: "Niet bevoegd",
  },
};

function buildRegisterUrl(diploma) {
  const params = new URLSearchParams({ role: "worker" });
  const types = [];
  if (diploma.kdv_status !== "not_qualified") types.push("kdv");
  if (diploma.bso_status !== "not_qualified") types.push("bso");
  if (types.length) params.set("opvangtype", types.join(","));
  if (diploma.kdv_status === "proof_required") params.set("kdv_proof", "1");
  if (diploma.bso_status === "proof_required") params.set("bso_proof", "1");
  return `/register?${params.toString()}`;
}

export default function HomeDiplomaCheck() {
  const [query, setQuery] = useState("");
  const [suggestions, setSuggestions] = useState([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const [selected, setSelected] = useState(null);
  const [loading, setLoading] = useState(false);
  const debounceRef = useRef(null);

  useEffect(() => {
    if (query.length < 2) { setSuggestions([]); setShowDropdown(false); return; }
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(async () => {
      setLoading(true);
      try {
        const data = await api.get(`/diplomacheck/search/?q=${encodeURIComponent(query)}`);
        setSuggestions(data);
        setShowDropdown(true);
      } catch { setSuggestions([]); }
      finally { setLoading(false); }
    }, 300);
  }, [query]);

  const handleSelect = async (diploma) => {
    setShowDropdown(false);
    setQuery(diploma.name);
    setLoading(true);
    try {
      const detail = await api.get(`/diplomacheck/${diploma.id}/`);
      setSelected(detail);
    } catch { setSelected(null); }
    finally { setLoading(false); }
  };

  const qualifiesAnywhere =
    selected &&
    (selected.kdv_status !== "not_qualified" || selected.bso_status !== "not_qualified");

  return (
    <section className="py-16 sm:py-24 px-6 bg-gray-50 border-y border-gray-100">
      <div className="max-w-2xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <span className="inline-flex items-center gap-1.5 bg-blue-100 text-blue-700 text-xs font-semibold px-3 py-1 rounded-full mb-4">
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            Diplomacheck
          </span>
          <h2 className="text-2xl sm:text-3xl font-bold text-gray-900 mb-3">
            Ontdek waar jij kunt werken
          </h2>
          <p className="text-gray-500 text-sm sm:text-base max-w-md mx-auto">
            Zoek je diploma en zie direct of je bevoegd bent voor KDV of BSO.
          </p>
        </div>

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
              type="text"
              value={query}
              onChange={(e) => { setQuery(e.target.value); setSelected(null); }}
              onFocus={() => suggestions.length > 0 && setShowDropdown(true)}
              placeholder="Typ je diplomanaam of CREBO-nummer..."
              className="w-full pl-12 pr-4 py-4 border border-gray-200 rounded-xl bg-white shadow-sm text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          {/* Dropdown */}
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
          <div className="mt-5 space-y-4">
            {/* KDV + BSO kaarten */}
            <div className="grid grid-cols-2 gap-3">
              {[
                { key: "kdv_status", title: "KDV", sub: "Kinderdagverblijf" },
                { key: "bso_status", title: "BSO", sub: "Buitenschoolse opvang" },
              ].map(({ key, title, sub }) => {
                const status = selected[key] || "not_qualified";
                const cfg = STATUS_CONFIG[status];
                return (
                  <div key={key} className={`rounded-xl border p-4 ${cfg.border}`}>
                    <div className="flex items-center gap-2 mb-1">
                      {cfg.icon}
                      <span className="font-semibold text-gray-900 text-sm">{title}</span>
                    </div>
                    <p className="text-xs text-gray-400 mb-2">{sub}</p>
                    <span className={`inline-block text-xs font-medium px-2 py-0.5 rounded-full ${cfg.badge}`}>
                      {cfg.label}
                    </span>
                  </div>
                );
              })}
            </div>

            {/* CTA */}
            {qualifiesAnywhere ? (
              <div className="bg-blue-700 rounded-xl p-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                <div>
                  <p className="text-white font-semibold text-sm">Klaar om te solliciteren?</p>
                  <p className="text-blue-200 text-xs mt-0.5">
                    Maak gratis een profiel aan en vind vacatures die bij jou passen.
                  </p>
                </div>
                <Link
                  href={buildRegisterUrl(selected)}
                  className="shrink-0 bg-white text-blue-700 font-semibold px-5 py-2.5 rounded-lg hover:bg-blue-50 transition-colors text-sm whitespace-nowrap"
                >
                  Gratis profiel →
                </Link>
              </div>
            ) : (
              <div className="bg-white border border-gray-100 rounded-xl p-4 text-center">
                <p className="text-sm text-gray-500 mb-2">
                  Dit diploma kwalificeert niet direct voor KDV of BSO.
                </p>
                <Link href="/diplomacheck" className="text-sm text-blue-700 hover:underline font-medium">
                  Bekijk volledige diplomacheck →
                </Link>
              </div>
            )}
          </div>
        )}

        {/* Footer link */}
        {!selected && (
          <p className="text-center text-xs text-gray-400 mt-4">
            Meer details?{" "}
            <Link href="/diplomacheck" className="text-blue-600 hover:underline">
              Ga naar de volledige diplomacheck
            </Link>
          </p>
        )}
      </div>
    </section>
  );
}

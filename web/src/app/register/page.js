"use client";

import { useState, useEffect, useRef, Suspense } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";

const ROLE_OPTIONS = [
  {
    value: "worker",
    label: "Ik ben een kinderopvang professional",
    desc: "Ik zoek een baan in de kinderopvang",
    icon: "👤",
  },
  {
    value: "institution",
    label: "Ik ben een kinderopvangorganisatie",
    desc: "Ik wil gratis vacatures plaatsen en professionals vinden",
    icon: "🏫",
  },
];

const OPVANGTYPE_OPTIONS = [
  { value: "kdv",     label: "KDV",       desc: "Kinderdagverblijf / Dagopvang" },
  { value: "0_2_jaar", label: "0-2 jaar",  desc: "Dagopvang voor baby's en dreumesen" },
  { value: "2_4_jaar", label: "2-4 jaar",  desc: "Dagopvang voor peuters" },
  { value: "bso",     label: "BSO",       desc: "Buitenschoolse opvang" },
];

const LEVEL_COLORS = {
  mbo2: "bg-gray-100 text-gray-600",
  mbo3: "bg-blue-50 text-blue-600",
  mbo4: "bg-blue-100 text-blue-700",
  hbo: "bg-purple-50 text-purple-700",
  wo: "bg-purple-100 text-purple-800",
};

function DiplomaCheckInline({ onResult }) {
  const [query, setQuery] = useState("");
  const [suggestions, setSuggestions] = useState([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const [searching, setSearching] = useState(false);
  const debounceRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    if (query.length < 2) { setSuggestions([]); setShowDropdown(false); return; }
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(async () => {
      setSearching(true);
      try {
        const data = await api.get(`/diplomacheck/search/?q=${encodeURIComponent(query)}`);
        setSuggestions(data);
        setShowDropdown(true);
      } catch { setSuggestions([]); }
      finally { setSearching(false); }
    }, 300);
  }, [query]);

  const handleSelect = async (diploma) => {
    setShowDropdown(false);
    setQuery(diploma.name);
    setSearching(true);
    try {
      const detail = await api.get(`/diplomacheck/${diploma.id}/`);
      onResult(detail);
    } catch { onResult(null); }
    finally { setSearching(false); }
  };

  return (
    <div className="relative">
      <div className="relative">
        <div className="absolute inset-y-0 left-3 flex items-center pointer-events-none">
          {searching ? (
            <svg className="w-4 h-4 text-blue-400 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
            </svg>
          ) : (
            <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          )}
        </div>
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => { setQuery(e.target.value); onResult(null); }}
          onFocus={() => suggestions.length > 0 && setShowDropdown(true)}
          placeholder="Zoek je diploma of CREBO-nummer..."
          className="w-full pl-9 pr-3 py-2.5 border border-gray-200 rounded-lg bg-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-200 focus:border-blue-400"
        />
      </div>
      {showDropdown && suggestions.length > 0 && (
        <div className="absolute z-20 w-full mt-1 bg-white border border-gray-100 rounded-xl shadow-lg overflow-hidden">
          {suggestions.map((d) => (
            <button
              key={d.id}
              type="button"
              onClick={() => handleSelect(d)}
              className="w-full text-left px-4 py-2.5 hover:bg-blue-50 transition-colors flex items-center justify-between gap-3 border-b border-gray-50 last:border-0"
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
      {showDropdown && suggestions.length === 0 && query.length >= 2 && !searching && (
        <div className="absolute z-20 w-full mt-1 bg-white border border-gray-100 rounded-xl shadow-lg px-4 py-3 text-sm text-gray-400">
          Geen diploma gevonden voor &ldquo;{query}&rdquo;
        </div>
      )}
    </div>
  );
}

function RegisterPageInner() {
  const { register } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();

  // URL params van diplomacheck
  const opvangtypeParam = searchParams.get("opvangtype") || "";
  const kdvProofParam = searchParams.get("kdv_proof") === "1";
  const bsoProofParam = searchParams.get("bso_proof") === "1";

  const initialOpvangtype = opvangtypeParam
    ? opvangtypeParam.split(",").filter(Boolean)
    : [];

  const roleParam = searchParams.get("role") || "";
  const [step, setStep] = useState(roleParam === "worker" ? 2 : 1);
  const [form, setForm] = useState({
    role: roleParam === "worker" ? "worker" : "",
    firstName: "",
    lastName: "",
    username: "",
    email: "",
    password: "",
    passwordConfirm: "",
  });
  const [opvangtype, setOpvangtype] = useState(initialOpvangtype);
  const [kdvProof, setKdvProof] = useState(kdvProofParam);
  const [bsoProof, setBsoProof] = useState(bsoProofParam);
  const [diplomaResult, setDiplomaResult] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleRoleSelect = (role) => {
    setForm((f) => ({ ...f, role }));
    setStep(2);
  };

  const toggleOpvangtype = (value) => {
    setOpvangtype((prev) =>
      prev.includes(value) ? prev.filter((v) => v !== value) : [...prev, value]
    );
  };

  const handleDiplomaResult = (diploma) => {
    setDiplomaResult(diploma);
    if (!diploma) return;
    const types = [];
    if (diploma.kdv_status !== "not_qualified") types.push("kdv");
    if (diploma.bso_status !== "not_qualified") types.push("bso");
    setOpvangtype(types);
    setKdvProof(diploma.kdv_status === "proof_required");
    setBsoProof(diploma.bso_status === "proof_required");
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    if (form.password !== form.passwordConfirm) {
      setError("Wachtwoorden komen niet overeen.");
      return;
    }

    setLoading(true);
    try {
      await register({
        username: form.username,
        email: form.email,
        password: form.password,
        role: form.role,
        first_name: form.firstName,
        last_name: form.lastName,
        opvangtype,
        kdv_proof_required: kdvProof,
        bso_proof_required: bsoProof,
      });
      router.push("/dashboard");
    } catch (err) {
      const messages = Object.values(err || {}).flat();
      setError(messages[0] || "Registratie mislukt.");
    } finally {
      setLoading(false);
    }
  };

  const selectedRole = ROLE_OPTIONS.find((r) => r.value === form.role);
  const cameFromDiplomaCheck = opvangtypeParam.length > 0;

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <div className="px-4 sm:px-8 py-4 sm:py-5 border-b border-gray-100 bg-white">
        <Link href="/" className="text-xl font-bold text-blue-700">
          KinderopvangBaan<span className="text-gray-400 font-medium text-xs">.nl</span>
        </Link>
      </div>

      <div className="flex flex-1 items-center justify-center px-4 py-16">
        <div className="w-full max-w-md">
          {/* Stap 1: rol kiezen */}
          {step === 1 && (
            <div>
              <h1 className="text-xl font-bold text-gray-900 mb-1 text-center">
                Maak een <span className="text-green-600">gratis</span> account aan
              </h1>
              <p className="text-sm text-gray-400 text-center mb-8">Wie ben jij?</p>

              <div className="space-y-3">
                {ROLE_OPTIONS.map((option) => (
                  <button
                    key={option.value}
                    onClick={() => handleRoleSelect(option.value)}
                    className="w-full flex items-center gap-4 bg-white rounded-2xl p-5 border border-gray-100 shadow-sm hover:border-blue-200 hover:shadow-md transition-all text-left group"
                  >
                    <span className="text-3xl">{option.icon}</span>
                    <div>
                      <div className="font-semibold text-gray-900 group-hover:text-blue-700 transition-colors">
                        {option.label}
                      </div>
                      <div className="text-sm text-gray-400 mt-0.5">{option.desc}</div>
                    </div>
                    <span className="ml-auto text-gray-200 group-hover:text-blue-300 transition-colors text-lg">→</span>
                  </button>
                ))}
              </div>

              <p className="text-center text-sm text-gray-400 mt-6">
                Al een account?{" "}
                <Link href="/login" className="text-blue-700 hover:underline">Inloggen</Link>
              </p>
            </div>
          )}

          {/* Stap 2: gegevens */}
          {step === 2 && (
            <div className="bg-white rounded-2xl p-8 shadow-sm border border-gray-100">
              <button
                onClick={() => setStep(1)}
                className="flex items-center gap-1 text-xs text-gray-400 hover:text-gray-600 transition-colors mb-6"
              >
                ← Terug
              </button>

              <div className="flex items-center gap-3 mb-6 pb-6 border-b border-gray-50">
                <span className="text-2xl">{selectedRole?.icon}</span>
                <div>
                  <div className="font-semibold text-gray-900 text-sm">{selectedRole?.label}</div>
                  <div className="text-xs text-gray-400">{selectedRole?.desc}</div>
                </div>
              </div>

              <form onSubmit={handleSubmit} className="space-y-4">
                {/* Opvangtype sectie — alleen voor workers */}
                {form.role === "worker" && (
                  <div className="rounded-xl border border-gray-100 bg-gray-50 p-4 space-y-3">
                    <div>
                      <p className="text-xs font-semibold text-gray-700 mb-0.5">Waarvoor ben jij bevoegd?</p>
                      <p className="text-xs text-gray-400">
                        {cameFromDiplomaCheck
                          ? "Ingevuld op basis van jouw diplomacheck. Je kunt dit aanpassen."
                          : "Doe optioneel de diplomacheck of selecteer handmatig."}
                      </p>
                    </div>

                    {/* Mini diplomacheck — alleen tonen als niet via URL params */}
                    {!cameFromDiplomaCheck && (
                      <div>
                        <label className="block text-xs text-gray-500 mb-1.5">
                          Zoek je diploma <span className="text-gray-400">(optioneel)</span>
                        </label>
                        <DiplomaCheckInline onResult={handleDiplomaResult} />
                        {diplomaResult && (
                          <p className="mt-2 text-xs text-gray-500">
                            Gevonden: <span className="font-medium text-gray-700">{diplomaResult.name}</span>
                            {" — "}
                            {diplomaResult.kdv_status !== "not_qualified" && (
                              <span className="text-green-600 font-medium">KDV ✓</span>
                            )}
                            {diplomaResult.kdv_status !== "not_qualified" && diplomaResult.bso_status !== "not_qualified" && " · "}
                            {diplomaResult.bso_status !== "not_qualified" && (
                              <span className="text-green-600 font-medium">BSO ✓</span>
                            )}
                          </p>
                        )}
                      </div>
                    )}

                    {/* Checkboxes */}
                    <div>
                      <label className="block text-xs text-gray-500 mb-2">Opvangtype</label>
                      <div className="grid grid-cols-2 gap-2">
                        {OPVANGTYPE_OPTIONS.map((opt) => {
                          const checked = opvangtype.includes(opt.value);
                          const isProof =
                            (opt.value === "kdv" && kdvProof) ||
                            (opt.value === "bso" && bsoProof);
                          return (
                            <button
                              key={opt.value}
                              type="button"
                              onClick={() => toggleOpvangtype(opt.value)}
                              className={`text-left px-3 py-2.5 rounded-lg border text-xs transition-all ${
                                checked
                                  ? "border-blue-300 bg-blue-50 text-blue-800"
                                  : "border-gray-200 bg-white text-gray-500 hover:border-gray-300"
                              }`}
                            >
                              <div className="flex items-center gap-1.5">
                                <span className={`w-3.5 h-3.5 rounded flex items-center justify-center shrink-0 ${checked ? "bg-blue-600" : "bg-white border border-gray-300"}`}>
                                  {checked && (
                                    <svg className="w-2.5 h-2.5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                                    </svg>
                                  )}
                                </span>
                                <span className="font-medium">{opt.label}</span>
                                {isProof && checked && (
                                  <span className="ml-auto text-amber-500 text-xs">*</span>
                                )}
                              </div>
                              <p className="mt-0.5 text-gray-400 pl-5">{opt.desc}</p>
                            </button>
                          );
                        })}
                      </div>
                      {(kdvProof || bsoProof) && opvangtype.some((t) => (t === "kdv" && kdvProof) || (t === "bso" && bsoProof)) && (
                        <p className="mt-2 text-xs text-amber-600">
                          * Bevoegd met aanvullend bewijs vereist. Je kunt gewoon solliciteren, maar een werkgever kan om bewijs vragen.
                        </p>
                      )}
                    </div>
                  </div>
                )}

                {/* Naam */}
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1.5">Voornaam</label>
                    <input
                      type="text"
                      value={form.firstName}
                      onChange={(e) => setForm((f) => ({ ...f, firstName: e.target.value }))}
                      autoFocus
                      autoComplete="given-name"
                      className="w-full border border-gray-200 rounded-lg px-3 py-2.5 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-200 focus:border-blue-400"
                      placeholder="Voornaam"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1.5">Achternaam</label>
                    <input
                      type="text"
                      value={form.lastName}
                      onChange={(e) => setForm((f) => ({ ...f, lastName: e.target.value }))}
                      autoComplete="family-name"
                      className="w-full border border-gray-200 rounded-lg px-3 py-2.5 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-200 focus:border-blue-400"
                      placeholder="Achternaam"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1.5">Gebruikersnaam</label>
                  <input
                    type="text"
                    value={form.username}
                    onChange={(e) => setForm((f) => ({ ...f, username: e.target.value }))}
                    required
                    autoComplete="username"
                    className="w-full border border-gray-200 rounded-lg px-3 py-2.5 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-200 focus:border-blue-400"
                    placeholder="jouwgebruikersnaam"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1.5">E-mailadres</label>
                  <input
                    type="email"
                    value={form.email}
                    onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
                    required
                    autoComplete="email"
                    className="w-full border border-gray-200 rounded-lg px-3 py-2.5 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-200 focus:border-blue-400"
                    placeholder="jouw@email.nl"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1.5">Wachtwoord</label>
                  <input
                    type="password"
                    value={form.password}
                    onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
                    required
                    minLength={8}
                    autoComplete="new-password"
                    className="w-full border border-gray-200 rounded-lg px-3 py-2.5 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-200 focus:border-blue-400"
                    placeholder="Minimaal 8 tekens"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1.5">Wachtwoord bevestigen</label>
                  <input
                    type="password"
                    value={form.passwordConfirm}
                    onChange={(e) => setForm((f) => ({ ...f, passwordConfirm: e.target.value }))}
                    required
                    autoComplete="new-password"
                    className="w-full border border-gray-200 rounded-lg px-3 py-2.5 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-200 focus:border-blue-400"
                    placeholder="••••••••"
                  />
                </div>

                {error && (
                  <div className="text-xs text-red-600 bg-red-50 border border-red-100 rounded-lg px-3 py-2">
                    {error}
                  </div>
                )}

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full bg-blue-700 text-white font-semibold py-2.5 rounded-lg hover:bg-blue-800 transition-colors disabled:opacity-60 disabled:cursor-not-allowed text-sm"
                >
                  {loading ? "Bezig..." : "Account aanmaken"}
                </button>

                <p className="text-xs text-gray-400 text-center">
                  Door te registreren ga je akkoord met onze{" "}
                  <Link href="/voorwaarden" className="text-blue-700 hover:underline">algemene voorwaarden</Link>.
                </p>
              </form>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function RegisterPage() {
  return (
    <Suspense fallback={null}>
      <RegisterPageInner />
    </Suspense>
  );
}

"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/context/AuthContext";
import Nav from "@/components/Nav";
import { CAO_FUNCTIONS } from "@/lib/caoFunctions";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";
const PDOK_URL = "https://api.pdok.nl/bzk/locatieserver/search/v3_1/free";

function getToken() {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("kb_access");
}

async function authRequest(path, options = {}) {
  const token = getToken();
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers || {}),
    },
  });
  if (!res.ok) throw await res.json();
  return res.json();
}

const AVAILABILITY_DAYS = ["ma", "di", "wo", "do", "vr", "za", "zo"];
const DAY_LABELS = { ma: "Ma", di: "Di", wo: "Wo", do: "Do", vr: "Vr", za: "Za", zo: "Zo" };

const BEVOEGDHEID_OPTIONS = [
  { value: "dagopvang", label: "Dagopvang", desc: "0–4 jaar" },
  { value: "bso", label: "BSO", desc: "Buitenschoolse opvang" },
  { value: "peuterspeelzaal", label: "Peuterspeelzaal", desc: "2.5–4 jaar" },
];

const CONTRACT_OPTIONS = [
  { value: "fulltime", label: "Fulltime" },
  { value: "parttime", label: "Parttime" },
  { value: "flex", label: "Flex / oproep" },
];

function Checkbox({ checked, onChange, label, desc }) {
  return (
    <label className="flex items-center gap-3 cursor-pointer group">
      <div
        onClick={onChange}
        className={`w-5 h-5 rounded flex items-center justify-center border-2 transition-colors flex-shrink-0 ${
          checked ? "bg-blue-700 border-blue-700" : "border-gray-300"
        }`}
      >
        {checked && (
          <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
          </svg>
        )}
      </div>
      <div>
        <div className="text-sm font-medium text-gray-700">{label}</div>
        {desc && <div className="text-xs text-gray-400">{desc}</div>}
      </div>
    </label>
  );
}

export default function WorkerProfilePage() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState(null);
  const [pdokLoading, setPdokLoading] = useState(false);

  const [form, setForm] = useState({
    bio: "",
    work_radius_km: 15,
    has_diploma: false,
    bevoegdheid: [],
    cao_function: "",
    contract_types: [],
    years_experience: "",
    hours_per_week: "",
    immediate_available: false,
    available_days: [],
    available_from: "",
    postcode: "",
    house_number: "",
    street: "",
    city: "",
  });

  useEffect(() => {
    if (!authLoading && !user) router.push("/login");
  }, [user, authLoading, router]);

  useEffect(() => {
    if (!user) return;
    authRequest("/auth/worker-profile/")
      .then((data) => {
        setForm({
          bio: data.bio || "",
          work_radius_km: data.work_radius_km || 15,
          has_diploma: data.has_diploma || false,
          bevoegdheid: data.bevoegdheid || [],
          cao_function: data.cao_function || "",
          contract_types: (data.contract_types || []).filter((c) => c !== "zzp"),
          years_experience: data.years_experience ?? "",
          hours_per_week: data.hours_per_week ?? "",
          immediate_available: data.immediate_available || false,
          available_days: data.availability?.days || [],
          available_from: data.availability?.from || "",
          postcode: data.postcode || "",
          house_number: data.house_number || "",
          street: data.street || "",
          city: data.city || "",
        });
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [user]);

  const pdokLookup = useCallback(async (postcode, houseNumber) => {
    if (!postcode || !houseNumber) return;
    const cleaned = postcode.replace(/\s/g, "").toUpperCase();
    if (!/^\d{4}[A-Z]{2}$/.test(cleaned)) return;
    setPdokLoading(true);
    try {
      const url = `${PDOK_URL}?q=${cleaned}+${houseNumber}&fq=type:adres&rows=1&fl=straatnaam,woonplaatsnaam`;
      const res = await fetch(url);
      const json = await res.json();
      const doc = json?.response?.docs?.[0];
      if (doc) {
        setForm((f) => ({
          ...f,
          street: doc.straatnaam || f.street,
          city: doc.woonplaatsnaam || f.city,
        }));
      }
    } catch {
      // PDOK fout — stil falen
    } finally {
      setPdokLoading(false);
    }
  }, []);

  const handlePostcodeBlur = () => {
    pdokLookup(form.postcode, form.house_number);
  };

  const handleHouseNumberBlur = () => {
    pdokLookup(form.postcode, form.house_number);
  };

  const toggleDay = (day) => {
    setForm((f) => ({
      ...f,
      available_days: f.available_days.includes(day)
        ? f.available_days.filter((d) => d !== day)
        : [...f.available_days, day],
    }));
  };

  const toggleBevoegdheid = (val) => {
    setForm((f) => ({
      ...f,
      bevoegdheid: f.bevoegdheid.includes(val)
        ? f.bevoegdheid.filter((v) => v !== val)
        : [...f.bevoegdheid, val],
    }));
  };

  const toggleContract = (val) => {
    setForm((f) => ({
      ...f,
      contract_types: f.contract_types.includes(val)
        ? f.contract_types.filter((v) => v !== val)
        : [...f.contract_types, val],
    }));
  };

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setSaved(false);
    try {
      await authRequest("/auth/worker-profile/", {
        method: "PATCH",
        body: JSON.stringify({
          bio: form.bio,
          work_radius_km: Number(form.work_radius_km),
          has_diploma: form.has_diploma,
          bevoegdheid: form.bevoegdheid,
          cao_function: form.cao_function,
          contract_types: form.contract_types,
          years_experience: form.years_experience !== "" ? Number(form.years_experience) : null,
          hours_per_week: form.hours_per_week !== "" ? Number(form.hours_per_week) : null,
          immediate_available: form.immediate_available,
          availability: { days: form.available_days, from: form.available_from },
          postcode: form.postcode,
          house_number: form.house_number,
          street: form.street,
          city: form.city,
        }),
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch {
      setError("Opslaan mislukt. Probeer opnieuw.");
    } finally {
      setSaving(false);
    }
  };

  if (authLoading || loading) {
    return (
      <div className="min-h-screen bg-white">
        <Nav />
        <div className="flex items-center justify-center py-32 text-gray-400">Laden...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Nav />
      <div className="max-w-2xl mx-auto px-4 sm:px-6 py-8 sm:py-10">
        <div className="flex items-center gap-3 mb-8">
          <Link href="/dashboard" className="text-xs text-gray-400 hover:text-gray-600">← Dashboard</Link>
          <span className="text-xs text-gray-200">/</span>
          <span className="text-xs text-gray-500">Mijn profiel</span>
        </div>

        <h1 className="text-xl font-bold text-gray-900 mb-6">Mijn profiel</h1>

        <form onSubmit={handleSave} className="space-y-5">
          {/* Over mij */}
          <div className="bg-white rounded-2xl p-6 border border-gray-100 shadow-sm">
            <h2 className="text-sm font-semibold text-gray-900 mb-4">Over mij</h2>
            <textarea
              value={form.bio}
              onChange={(e) => setForm((f) => ({ ...f, bio: e.target.value }))}
              placeholder="Vertel iets over jezelf, je ervaring en wat je zoekt..."
              rows={4}
              className="w-full border border-gray-200 rounded-lg px-3 py-2.5 text-sm text-gray-900 resize-none focus:outline-none focus:ring-2 focus:ring-blue-200"
            />
            <div className="mt-3">
              <label className="block text-xs font-medium text-gray-600 mb-1.5">
                Jaren werkervaring
              </label>
              <input
                type="number"
                min="0"
                max="50"
                value={form.years_experience}
                onChange={(e) => setForm((f) => ({ ...f, years_experience: e.target.value }))}
                className="w-24 border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-200"
                placeholder="0"
              />
            </div>
          </div>

          {/* CAO functie */}
          <div className="bg-white rounded-2xl p-6 border border-gray-100 shadow-sm">
            <h2 className="text-sm font-semibold text-gray-900 mb-1">Mijn functie</h2>
            <p className="text-xs text-gray-400 mb-3">Selecteer jouw CAO-functie uit de kinderopvang functielijst.</p>
            <select
              value={form.cao_function}
              onChange={(e) => setForm((f) => ({ ...f, cao_function: e.target.value }))}
              className="w-full border border-gray-200 rounded-lg px-3 py-2.5 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-200 bg-white"
            >
              <option value="">— Selecteer een functie —</option>
              {CAO_FUNCTIONS.map((fn) => (
                <option key={fn.value} value={fn.value}>{fn.label}</option>
              ))}
            </select>
          </div>

          {/* Locatie */}
          <div className="bg-white rounded-2xl p-6 border border-gray-100 shadow-sm">
            <h2 className="text-sm font-semibold text-gray-900 mb-1">Locatie</h2>
            <p className="text-xs text-gray-400 mb-4">
              Vul je postcode en huisnummer in — straat en woonplaats worden automatisch ingevuld.
            </p>
            <div className="grid grid-cols-2 gap-3 mb-3">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1.5">Postcode</label>
                <input
                  type="text"
                  value={form.postcode}
                  onChange={(e) => setForm((f) => ({ ...f, postcode: e.target.value }))}
                  onBlur={handlePostcodeBlur}
                  placeholder="1234AB"
                  maxLength={7}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2.5 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-200"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1.5">Huisnummer</label>
                <input
                  type="text"
                  value={form.house_number}
                  onChange={(e) => setForm((f) => ({ ...f, house_number: e.target.value }))}
                  onBlur={handleHouseNumberBlur}
                  placeholder="12A"
                  maxLength={10}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2.5 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-200"
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1.5">
                  Straat {pdokLoading && <span className="text-gray-400">(zoeken...)</span>}
                </label>
                <input
                  type="text"
                  value={form.street}
                  onChange={(e) => setForm((f) => ({ ...f, street: e.target.value }))}
                  placeholder="Automatisch ingevuld"
                  className="w-full border border-gray-200 rounded-lg px-3 py-2.5 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-200 bg-gray-50"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1.5">Woonplaats</label>
                <input
                  type="text"
                  value={form.city}
                  onChange={(e) => setForm((f) => ({ ...f, city: e.target.value }))}
                  placeholder="Automatisch ingevuld"
                  className="w-full border border-gray-200 rounded-lg px-3 py-2.5 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-200 bg-gray-50"
                />
              </div>
            </div>
          </div>

          {/* Bevoegdheid */}
          <div className="bg-white rounded-2xl p-6 border border-gray-100 shadow-sm">
            <h2 className="text-sm font-semibold text-gray-900 mb-1">Bevoegdheid</h2>
            <p className="text-xs text-gray-400 mb-4">Selecteer de opvangvormen waarvoor jij bevoegd bent.</p>
            <div className="space-y-3">
              {BEVOEGDHEID_OPTIONS.map((opt) => (
                <Checkbox
                  key={opt.value}
                  checked={form.bevoegdheid.includes(opt.value)}
                  onChange={() => toggleBevoegdheid(opt.value)}
                  label={opt.label}
                  desc={opt.desc}
                />
              ))}
              <Checkbox
                checked={form.has_diploma}
                onChange={() => setForm((f) => ({ ...f, has_diploma: !f.has_diploma }))}
                label="Diploma behaald"
                desc="SPW / Pedagogisch Werker 3 of hoger"
              />
            </div>
          </div>

          {/* Dienstverband */}
          <div className="bg-white rounded-2xl p-6 border border-gray-100 shadow-sm">
            <h2 className="text-sm font-semibold text-gray-900 mb-4">Dienstverband</h2>
            <div className="space-y-3">
              {CONTRACT_OPTIONS.map((opt) => (
                <Checkbox
                  key={opt.value}
                  checked={form.contract_types.includes(opt.value)}
                  onChange={() => toggleContract(opt.value)}
                  label={opt.label}
                />
              ))}
            </div>
            <div className="mt-4">
              <label className="block text-xs font-medium text-gray-600 mb-1.5">
                Uren per week (gewenst)
              </label>
              <input
                type="number"
                min="1"
                max="40"
                value={form.hours_per_week}
                onChange={(e) => setForm((f) => ({ ...f, hours_per_week: e.target.value }))}
                className="w-24 border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-200"
                placeholder="32"
              />
            </div>
          </div>

          {/* Beschikbaarheid */}
          <div className="bg-white rounded-2xl p-6 border border-gray-100 shadow-sm">
            <h2 className="text-sm font-semibold text-gray-900 mb-4">Beschikbaarheid</h2>

            {/* Per direct toggle */}
            <div className="flex items-center justify-between mb-4 pb-4 border-b border-gray-50">
              <div>
                <div className="text-sm font-medium text-gray-700">Per direct beschikbaar</div>
                <div className="text-xs text-gray-400">Ik kan zo snel mogelijk beginnen</div>
              </div>
              <button
                type="button"
                onClick={() => setForm((f) => ({ ...f, immediate_available: !f.immediate_available }))}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  form.immediate_available ? "bg-blue-700" : "bg-gray-200"
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform ${
                    form.immediate_available ? "translate-x-6" : "translate-x-1"
                  }`}
                />
              </button>
            </div>

            <div className="mb-4">
              <div className="text-xs font-medium text-gray-500 mb-2">Beschikbare dagen</div>
              <div className="flex gap-2 flex-wrap">
                {AVAILABILITY_DAYS.map((day) => (
                  <button
                    key={day}
                    type="button"
                    onClick={() => toggleDay(day)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                      form.available_days.includes(day)
                        ? "bg-blue-700 text-white"
                        : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                    }`}
                  >
                    {DAY_LABELS[day]}
                  </button>
                ))}
              </div>
            </div>

            {!form.immediate_available && (
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1.5">Beschikbaar vanaf</label>
                <input
                  type="date"
                  value={form.available_from}
                  onChange={(e) => setForm((f) => ({ ...f, available_from: e.target.value }))}
                  className="border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-200"
                />
              </div>
            )}
          </div>

          {/* Zoekradius */}
          <div className="bg-white rounded-2xl p-6 border border-gray-100 shadow-sm">
            <h2 className="text-sm font-semibold text-gray-900 mb-1">Zoekradius</h2>
            <p className="text-xs text-gray-400 mb-4">
              Vacatures en instellingen worden gefilterd op deze afstand van jouw locatie.
            </p>
            <div className="flex gap-2 flex-wrap">
              {[5, 10, 15, 25, 50].map((r) => (
                <button
                  key={r}
                  type="button"
                  onClick={() => setForm((f) => ({ ...f, work_radius_km: r }))}
                  className={`px-4 py-2 rounded-xl text-sm font-semibold transition-colors ${
                    form.work_radius_km === r
                      ? "bg-blue-700 text-white shadow-sm"
                      : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                  }`}
                >
                  {r} km
                </button>
              ))}
            </div>
            <p className="text-xs text-gray-400 mt-3">
              Geselecteerd: <strong className="text-blue-700">{form.work_radius_km} km</strong>
              {" · "}Wordt toegepast op{" "}
              <Link href="/map" className="text-blue-600 hover:underline">Kaart</Link>{" "}en{" "}
              <Link href="/jobs" className="text-blue-600 hover:underline">Vacatures</Link>.
            </p>
          </div>

          {error && (
            <div className="text-xs text-red-600 bg-red-50 border border-red-100 rounded-lg px-4 py-2.5">
              {error}
            </div>
          )}

          <div className="flex items-center gap-4">
            <button
              type="submit"
              disabled={saving}
              className="bg-blue-700 text-white font-semibold px-6 py-2.5 rounded-lg hover:bg-blue-800 transition-colors disabled:opacity-60 text-sm"
            >
              {saving ? "Opslaan..." : "Opslaan"}
            </button>
            {saved && (
              <span className="text-sm text-green-600 font-medium">✓ Wijzigingen opgeslagen</span>
            )}
          </div>
        </form>
      </div>
    </div>
  );
}

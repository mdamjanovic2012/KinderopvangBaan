"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import Nav from "@/components/Nav";
import { CAO_FUNCTIONS } from "@/lib/caoFunctions";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

function getToken() {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("kb_access");
}

async function authPost(path, body) {
  const token = getToken();
  const res = await fetch(`${BASE_URL}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw await res.json();
  return res.json();
}

async function authGet(path) {
  const token = getToken();
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) },
  });
  if (!res.ok) throw await res.json();
  return res.json();
}

const JOB_TYPES = CAO_FUNCTIONS;

const CONTRACT_TYPES = [
  { value: "fulltime", label: "Full-time" },
  { value: "parttime", label: "Part-time" },
  { value: "temp", label: "Tijdelijk" },
];

const BEVOEGDHEID_OPTIONS = [
  { value: "dagopvang", label: "Dagopvang" },
  { value: "bso", label: "BSO" },
  { value: "peuterspeelzaal", label: "Peuterspeelzaal" },
];

const EMPTY_FORM = {
  title: "",
  job_type: "pm3",
  contract_type: "parttime",
  description: "",
  salary_min: "",
  salary_max: "",
  hours_per_week: "",
  min_experience: "",
  requires_bevoegdheid: [],
  requires_diploma: false,
  institution: "",
};

export default function NewVacaturePage() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();
  const [form, setForm] = useState(EMPTY_FORM);
  const [institutions, setInstitutions] = useState([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [fieldErrors, setFieldErrors] = useState({});

  useEffect(() => {
    if (!authLoading && !user) router.push("/login");
    if (!authLoading && user && user.role !== "institution") router.push("/dashboard");
  }, [user, authLoading, router]);

  useEffect(() => {
    if (!user) return;
    authGet("/institutions/?page_size=100")
      .then((data) => {
        const list = data.results || data;
        setInstitutions(list);
        if (list.length > 0) setForm((f) => ({ ...f, institution: list[0].id }));
      })
      .catch(() => {});
  }, [user]);

  const set = (key, value) => setForm((f) => ({ ...f, [key]: value }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setFieldErrors({});
    try {
      const payload = {
        ...form,
        salary_min: form.salary_min !== "" ? Number(form.salary_min) : null,
        salary_max: form.salary_max !== "" ? Number(form.salary_max) : null,
        hours_per_week: form.hours_per_week !== "" ? Number(form.hours_per_week) : null,
        min_experience: form.min_experience !== "" ? Number(form.min_experience) : null,
        institution: Number(form.institution),
      };
      const job = await authPost("/jobs/", payload);
      router.push(`/jobs/${job.id}`);
    } catch (err) {
      if (typeof err === "object" && !err.detail) {
        setFieldErrors(err);
        setError("Controleer de velden hieronder.");
      } else {
        setError(err?.detail || "Opslaan mislukt.");
      }
    } finally {
      setSaving(false);
    }
  };

  if (authLoading) return null;

  const inputCls = (field) =>
    `w-full border rounded-lg px-3 py-2.5 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-200 focus:border-blue-400 ${
      fieldErrors[field] ? "border-red-300 bg-red-50" : "border-gray-200"
    }`;

  return (
    <div className="min-h-screen bg-gray-50">
      <Nav />
      <div className="max-w-2xl mx-auto px-6 py-10">
        <div className="flex items-center gap-3 mb-8">
          <Link href="/dashboard/vacatures" className="text-xs text-gray-400 hover:text-gray-600">← Mijn vacatures</Link>
          <span className="text-xs text-gray-200">/</span>
          <span className="text-xs text-gray-500">Nieuwe vacature</span>
        </div>

        <h1 className="text-xl font-bold text-gray-900 mb-6">Vacature plaatsen</h1>

        <form onSubmit={handleSubmit} className="space-y-5">
          {/* Basis */}
          <div className="bg-white rounded-2xl p-6 border border-gray-100 shadow-sm space-y-4">
            <h2 className="text-sm font-semibold text-gray-900">Basisinformatie</h2>

            {institutions.length > 1 && (
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1.5">Instelling</label>
                <select
                  value={form.institution}
                  onChange={(e) => set("institution", e.target.value)}
                  className={inputCls("institution")}
                >
                  {institutions.map((inst) => (
                    <option key={inst.id} value={inst.id}>{inst.name} — {inst.city}</option>
                  ))}
                </select>
              </div>
            )}

            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1.5">Vacaturetitel *</label>
              <input
                type="text"
                required
                value={form.title}
                onChange={(e) => set("title", e.target.value)}
                className={inputCls("title")}
                placeholder="bijv. Pedagogisch medewerker BSO 24u"
              />
              {fieldErrors.title && <p className="text-xs text-red-500 mt-1">{fieldErrors.title[0]}</p>}
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1.5">Functietype *</label>
                <select value={form.job_type} onChange={(e) => set("job_type", e.target.value)} className={inputCls("job_type")}>
                  {JOB_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1.5">Contracttype *</label>
                <select value={form.contract_type} onChange={(e) => set("contract_type", e.target.value)} className={inputCls("contract_type")}>
                  {CONTRACT_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
                </select>
              </div>
            </div>
          </div>

          {/* Beschrijving */}
          <div className="bg-white rounded-2xl p-6 border border-gray-100 shadow-sm">
            <h2 className="text-sm font-semibold text-gray-900 mb-4">Omschrijving *</h2>
            <textarea
              required
              value={form.description}
              onChange={(e) => set("description", e.target.value)}
              rows={8}
              className={`${inputCls("description")} resize-none`}
              placeholder="Beschrijf de functie, taken, vereisten en wat je biedt..."
            />
            {fieldErrors.description && <p className="text-xs text-red-500 mt-1">{fieldErrors.description[0]}</p>}
          </div>

          {/* Arbeidsvoorwaarden */}
          <div className="bg-white rounded-2xl p-6 border border-gray-100 shadow-sm space-y-4">
            <h2 className="text-sm font-semibold text-gray-900">Arbeidsvoorwaarden</h2>
            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1.5">Salaris min (€/uur)</label>
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  value={form.salary_min}
                  onChange={(e) => set("salary_min", e.target.value)}
                  className={inputCls("salary_min")}
                  placeholder="13.50"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1.5">Salaris max (€/uur)</label>
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  value={form.salary_max}
                  onChange={(e) => set("salary_max", e.target.value)}
                  className={inputCls("salary_max")}
                  placeholder="18.00"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1.5">Uren/week</label>
                <input
                  type="number"
                  min="1"
                  max="40"
                  value={form.hours_per_week}
                  onChange={(e) => set("hours_per_week", e.target.value)}
                  className={inputCls("hours_per_week")}
                  placeholder="24"
                />
              </div>
            </div>
          </div>

          {/* Vereisten */}
          <div className="bg-white rounded-2xl p-6 border border-gray-100 shadow-sm space-y-4">
            <h2 className="text-sm font-semibold text-gray-900">Vereisten</h2>

            {/* Bevoegdheid vereist */}
            <div>
              <div className="text-xs font-medium text-gray-600 mb-2">Bevoegdheid vereist</div>
              <div className="space-y-2">
                {BEVOEGDHEID_OPTIONS.map(({ value, label }) => {
                  const checked = form.requires_bevoegdheid.includes(value);
                  return (
                    <label key={value} className="flex items-center gap-3 cursor-pointer">
                      <div
                        onClick={() =>
                          set(
                            "requires_bevoegdheid",
                            checked
                              ? form.requires_bevoegdheid.filter((v) => v !== value)
                              : [...form.requires_bevoegdheid, value]
                          )
                        }
                        className={`w-5 h-5 rounded flex items-center justify-center border-2 transition-colors flex-shrink-0 ${
                          checked ? "bg-blue-700 border-blue-700" : "border-gray-300"
                        }`}
                      >
                        {checked && <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7"/></svg>}
                      </div>
                      <span className="text-sm text-gray-700">{label}</span>
                    </label>
                  );
                })}
              </div>
            </div>

            {/* Diploma vereist */}
            <label className="flex items-center gap-3 cursor-pointer">
              <div
                onClick={() => set("requires_diploma", !form.requires_diploma)}
                className={`w-5 h-5 rounded flex items-center justify-center border-2 transition-colors flex-shrink-0 ${
                  form.requires_diploma ? "bg-blue-700 border-blue-700" : "border-gray-300"
                }`}
              >
                {form.requires_diploma && <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7"/></svg>}
              </div>
              <div>
                <div className="text-sm font-medium text-gray-700">Diploma vereist</div>
                <div className="text-xs text-gray-400">SPW / Pedagogisch Werker 3 of hoger</div>
              </div>
            </label>

            {/* Minimale werkervaring */}
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1.5">
                Minimale werkervaring (jaren)
              </label>
              <input
                type="number"
                min="0"
                max="20"
                value={form.min_experience}
                onChange={(e) => set("min_experience", e.target.value)}
                className={`w-24 ${inputCls("min_experience")}`}
                placeholder="0"
              />
              <p className="text-xs text-gray-400 mt-1">Laat leeg als geen minimum vereist is.</p>
            </div>
          </div>

          {error && (
            <div className="text-xs text-red-600 bg-red-50 border border-red-100 rounded-lg px-4 py-2.5">
              {error}
            </div>
          )}

          <div className="flex items-center gap-3">
            <button
              type="submit"
              disabled={saving}
              className="bg-blue-700 text-white font-semibold px-6 py-2.5 rounded-lg hover:bg-blue-800 transition-colors disabled:opacity-60 text-sm"
            >
              {saving ? "Plaatsen..." : "Vacature plaatsen"}
            </button>
            <Link href="/dashboard/vacatures" className="text-sm text-gray-400 hover:text-gray-600">
              Annuleren
            </Link>
          </div>
        </form>
      </div>
    </div>
  );
}

"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/context/AuthContext";
import Nav from "@/components/Nav";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

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
const DAY_LABELS = {
  ma: "Ma", di: "Di", wo: "Wo", do: "Do", vr: "Vr", za: "Za", zo: "Zo",
};

export default function WorkerProfilePage() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();

  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState(null);

  const [form, setForm] = useState({
    bio: "",
    work_radius_km: 15,
    has_vog: false,
    has_diploma: false,
    years_experience: "",
    available_days: [],
    available_from: "",
  });

  useEffect(() => {
    if (!authLoading && !user) router.push("/login");
  }, [user, authLoading, router]);

  useEffect(() => {
    if (!user) return;
    authRequest("/auth/worker-profile/")
      .then((data) => {
        setProfile(data);
        setForm({
          bio: data.bio || "",
          work_radius_km: data.work_radius_km || 15,
          has_vog: data.has_vog || false,
          has_diploma: data.has_diploma || false,
          years_experience: data.years_experience ?? "",
          available_days: data.availability?.days || [],
          available_from: data.availability?.from || "",
        });
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [user]);

  const toggleDay = (day) => {
    setForm((f) => ({
      ...f,
      available_days: f.available_days.includes(day)
        ? f.available_days.filter((d) => d !== day)
        : [...f.available_days, day],
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
          has_vog: form.has_vog,
          has_diploma: form.has_diploma,
          years_experience: form.years_experience !== "" ? Number(form.years_experience) : null,
          availability: {
            days: form.available_days,
            from: form.available_from,
          },
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
      <div className="max-w-2xl mx-auto px-6 py-10">
        <div className="flex items-center gap-3 mb-8">
          <Link href="/dashboard" className="text-xs text-gray-400 hover:text-gray-600">← Dashboard</Link>
          <span className="text-xs text-gray-200">/</span>
          <span className="text-xs text-gray-500">Mijn profiel</span>
        </div>

        <h1 className="text-xl font-bold text-gray-900 mb-6">Mijn profiel</h1>

        <form onSubmit={handleSave} className="space-y-5">
          {/* Bio */}
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

          {/* Certificaten */}
          <div className="bg-white rounded-2xl p-6 border border-gray-100 shadow-sm">
            <h2 className="text-sm font-semibold text-gray-900 mb-4">Certificaten & Kwalificaties</h2>
            <div className="space-y-3">
              <label className="flex items-center gap-3 cursor-pointer group">
                <div
                  onClick={() => setForm((f) => ({ ...f, has_vog: !f.has_vog }))}
                  className={`w-5 h-5 rounded flex items-center justify-center border-2 transition-colors ${
                    form.has_vog ? "bg-blue-700 border-blue-700" : "border-gray-300"
                  }`}
                >
                  {form.has_vog && <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7"/></svg>}
                </div>
                <div>
                  <div className="text-sm font-medium text-gray-700">VOG aanwezig</div>
                  <div className="text-xs text-gray-400">Verklaring Omtrent Gedrag</div>
                </div>
              </label>
              <label className="flex items-center gap-3 cursor-pointer">
                <div
                  onClick={() => setForm((f) => ({ ...f, has_diploma: !f.has_diploma }))}
                  className={`w-5 h-5 rounded flex items-center justify-center border-2 transition-colors ${
                    form.has_diploma ? "bg-blue-700 border-blue-700" : "border-gray-300"
                  }`}
                >
                  {form.has_diploma && <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7"/></svg>}
                </div>
                <div>
                  <div className="text-sm font-medium text-gray-700">Diploma behaald</div>
                  <div className="text-xs text-gray-400">SPW / Pedagogisch Werker 3 of hoger</div>
                </div>
              </label>
            </div>
          </div>

          {/* Beschikbaarheid */}
          <div className="bg-white rounded-2xl p-6 border border-gray-100 shadow-sm">
            <h2 className="text-sm font-semibold text-gray-900 mb-4">Beschikbaarheid</h2>
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
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1.5">Beschikbaar vanaf</label>
              <input
                type="date"
                value={form.available_from}
                onChange={(e) => setForm((f) => ({ ...f, available_from: e.target.value }))}
                className="border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-200"
              />
            </div>
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
              Geselecteerd: <strong className="text-blue-700">{form.work_radius_km} km</strong>{" · "}
              Wordt toegepast op{" "}
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

"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import Nav from "@/components/Nav";
import { useAuth } from "@/context/AuthContext";

const CONTRACT_LABELS = {
  fulltime: "Full-time",
  parttime: "Part-time",
  zzp: "ZZP / Freelance",
  temp: "Tijdelijk",
};

const JOB_TYPE_LABELS = {
  bso: "BSO medewerker",
  kdv: "Pedagogisch medewerker KDV",
  nanny: "Nanny",
  gastouder: "Gastouder",
};

export default function JobDetailPage({ params }) {
  const { id } = params;
  const { user } = useAuth();
  const router = useRouter();
  const [job, setJob] = useState(null);
  const [loading, setLoading] = useState(true);
  const [applying, setApplying] = useState(false);
  const [coverLetter, setCoverLetter] = useState("");
  const [applied, setApplied] = useState(false);
  const [applyError, setApplyError] = useState(null);

  useEffect(() => {
    api.job(id)
      .then(setJob)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) {
    return (
      <div className="min-h-screen bg-white">
        <Nav />
        <div className="flex items-center justify-center py-32 text-gray-400">Laden...</div>
      </div>
    );
  }

  if (!job) {
    return (
      <div className="min-h-screen bg-white">
        <Nav />
        <div className="flex flex-col items-center justify-center py-32 gap-4">
          <p className="text-gray-500">Vacature niet gevonden.</p>
          <Link href="/jobs" className="text-blue-700 hover:underline text-sm">Terug naar vacatures</Link>
        </div>
      </div>
    );
  }

  const postedDate = new Date(job.created_at).toLocaleDateString("nl-NL", {
    day: "numeric", month: "long", year: "numeric",
  });

  return (
    <div className="min-h-screen bg-gray-50">
      <Nav />

      <div className="max-w-4xl mx-auto px-4 sm:px-6 py-6 sm:py-8">
        {/* Breadcrumb */}
        <div className="flex items-center gap-2 text-sm text-gray-400 mb-6">
          <Link href="/jobs" className="hover:text-blue-700 transition-colors">Vacatures</Link>
          <span>/</span>
          <span className="text-gray-600 truncate">{job.title}</span>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main */}
          <div className="lg:col-span-2 space-y-6">
            <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
              <div className="flex items-center gap-2 mb-3 flex-wrap">
                <span className="text-xs font-medium px-2.5 py-1 rounded-full bg-blue-50 text-blue-600">
                  {CONTRACT_LABELS[job.contract_type] || job.contract_type}
                </span>
                <span className="text-xs font-medium px-2.5 py-1 rounded-full bg-gray-100 text-gray-600">
                  {JOB_TYPE_LABELS[job.job_type] || job.job_type}
                </span>
                {job.is_premium && (
                  <span className="text-xs font-medium px-2.5 py-1 rounded-full bg-yellow-50 text-yellow-600">
                    Uitgelicht
                  </span>
                )}
              </div>
              <h1 className="text-2xl font-bold text-gray-900 mb-1">{job.title}</h1>
              <div className="text-sm text-gray-500">
                <Link
                  href={`/instellingen/${job.institution}`}
                  className="font-medium text-gray-700 hover:text-blue-700 transition-colors"
                >
                  {job.institution_name}
                </Link>
                {" · "}
                {job.institution_city || job.city}
              </div>
            </div>

            <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
              <h2 className="text-sm font-semibold text-gray-900 mb-3">Omschrijving</h2>
              <div className="text-sm text-gray-600 leading-relaxed whitespace-pre-wrap">
                {job.description}
              </div>
            </div>

            <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
              <h2 className="text-sm font-semibold text-gray-900 mb-4">Vereisten</h2>
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <span className={`w-4 h-4 rounded-full flex items-center justify-center text-xs ${job.requires_vog ? "bg-red-100 text-red-600" : "bg-gray-100 text-gray-400"}`}>
                    {job.requires_vog ? "!" : "–"}
                  </span>
                  <span className="text-sm text-gray-600">
                    VOG (Verklaring Omtrent Gedrag) {job.requires_vog ? "vereist" : "niet vereist"}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`w-4 h-4 rounded-full flex items-center justify-center text-xs ${job.requires_diploma ? "bg-red-100 text-red-600" : "bg-gray-100 text-gray-400"}`}>
                    {job.requires_diploma ? "!" : "–"}
                  </span>
                  <span className="text-sm text-gray-600">
                    Diploma {job.requires_diploma ? "vereist" : "niet vereist"}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Sidebar */}
          <div className="space-y-4">
            {/* Apply CTA */}
            <div className="bg-blue-700 rounded-2xl p-5 text-white">
              <div className="text-sm font-semibold mb-3">Reageer op deze vacature</div>
              {applied ? (
                <div className="text-center text-sm bg-white text-green-700 rounded-lg py-2.5 font-semibold">
                  ✓ Sollicitatie verstuurd!
                </div>
              ) : applying ? (
                <div className="space-y-3">
                  <textarea
                    value={coverLetter}
                    onChange={(e) => setCoverLetter(e.target.value)}
                    placeholder="Korte motivatie (optioneel)..."
                    rows={4}
                    className="w-full rounded-lg px-3 py-2 text-sm text-gray-900 resize-none focus:outline-none focus:ring-2 focus:ring-blue-300"
                  />
                  {applyError && (
                    <div className="text-xs text-red-200">{applyError}</div>
                  )}
                  <div className="flex gap-2">
                    <button
                      onClick={async () => {
                        try {
                          await api.applyToJob(id, coverLetter);
                          setApplied(true);
                        } catch (err) {
                          setApplyError(err?.non_field_errors?.[0] || "Er ging iets mis.");
                        }
                      }}
                      className="flex-1 bg-white text-blue-700 font-semibold text-sm py-2 rounded-lg hover:bg-blue-50 transition-colors"
                    >
                      Versturen
                    </button>
                    <button
                      onClick={() => setApplying(false)}
                      className="text-sm text-blue-200 hover:text-white transition-colors px-2"
                    >
                      Annuleren
                    </button>
                  </div>
                </div>
              ) : user ? (
                <button
                  onClick={() => setApplying(true)}
                  className="w-full block text-center text-sm font-semibold bg-white text-blue-700 rounded-lg py-2.5 hover:bg-blue-50 transition-colors"
                >
                  Solliciteren
                </button>
              ) : (
                <Link
                  href={`/login?next=/jobs/${id}`}
                  className="block text-center text-sm font-semibold bg-white text-blue-700 rounded-lg py-2.5 hover:bg-blue-50 transition-colors"
                >
                  Inloggen om te reageren
                </Link>
              )}
            </div>

            {/* Job details */}
            <div className="bg-white rounded-2xl p-5 shadow-sm border border-gray-100 space-y-3">
              {(job.salary_min || job.salary_max) && (
                <div>
                  <div className="text-xs text-gray-400 mb-0.5">Salaris</div>
                  <div className="text-sm font-semibold text-gray-900">
                    €{job.salary_min}
                    {job.salary_max && job.salary_max !== job.salary_min && `–${job.salary_max}`}
                    <span className="text-xs font-normal text-gray-400"> per uur</span>
                  </div>
                </div>
              )}
              {job.hours_per_week && (
                <div>
                  <div className="text-xs text-gray-400 mb-0.5">Uren</div>
                  <div className="text-sm font-medium text-gray-700">{job.hours_per_week} uur per week</div>
                </div>
              )}
              <div>
                <div className="text-xs text-gray-400 mb-0.5">Contract</div>
                <div className="text-sm font-medium text-gray-700">
                  {CONTRACT_LABELS[job.contract_type] || job.contract_type}
                </div>
              </div>
              <div>
                <div className="text-xs text-gray-400 mb-0.5">Locatie</div>
                <div className="text-sm font-medium text-gray-700">{job.institution_city || job.city}</div>
              </div>
              <div>
                <div className="text-xs text-gray-400 mb-0.5">Geplaatst</div>
                <div className="text-sm font-medium text-gray-700">{postedDate}</div>
              </div>
            </div>

            {/* Institution link */}
            <Link
              href={`/instellingen/${job.institution}`}
              className="block bg-white rounded-2xl p-5 shadow-sm border border-gray-100 hover:border-blue-200 transition-colors group"
            >
              <div className="text-xs text-gray-400 mb-1">Werkgever</div>
              <div className="text-sm font-semibold text-gray-900 group-hover:text-blue-700 transition-colors">
                {job.institution_name}
              </div>
              <div className="text-xs text-gray-400 mt-0.5">{job.institution_city}</div>
              <div className="text-xs text-blue-700 mt-2">Bekijk profiel →</div>
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

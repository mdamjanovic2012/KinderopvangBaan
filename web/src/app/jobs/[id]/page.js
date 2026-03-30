"use client";

import { use, useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import Nav from "@/components/Nav";
import { useAuth } from "@/context/AuthContext";
import { getCaoLabel } from "@/lib/caoFunctions";

const CONTRACT_LABELS = {
  fulltime: "Full-time",
  parttime: "Part-time",
  temp: "Tijdelijk",
};

export default function JobDetailPage({ params }) {
  const { id } = typeof params?.then === "function" ? use(params) : params;
  const { user } = useAuth();
  const router = useRouter();
  const [job, setJob] = useState(null);
  const [loading, setLoading] = useState(true);
  const [redirecting, setRedirecting] = useState(false);

  useEffect(() => {
    api.job(id)
      .then(setJob)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [id]);

  const handleVisit = async () => {
    if (!user) {
      router.push(`/register?next=/jobs/${id}`);
      return;
    }
    setRedirecting(true);
    try {
      const { source_url } = await api.clickJob(id);
      window.open(source_url, "_blank", "noopener,noreferrer");
    } catch {
      // fallback: open source_url directly
      if (job?.source_url) window.open(job.source_url, "_blank", "noopener,noreferrer");
    } finally {
      setRedirecting(false);
    }
  };

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
                {job.contract_type && (
                  <span className="text-xs font-medium px-2.5 py-1 rounded-full bg-blue-50 text-blue-600">
                    {CONTRACT_LABELS[job.contract_type] || job.contract_type}
                  </span>
                )}
                {job.job_type && (
                  <span className="text-xs font-medium px-2.5 py-1 rounded-full bg-gray-100 text-gray-600">
                    {getCaoLabel(job.job_type)}
                  </span>
                )}
                {job.age_min != null && job.age_max != null && (
                  <span className="text-xs font-medium px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-600">
                    {job.age_min}–{job.age_max} jaar
                  </span>
                )}
                {job.is_premium && (
                  <span className="text-xs font-medium px-2.5 py-1 rounded-full bg-yellow-50 text-yellow-600">
                    Uitgelicht
                  </span>
                )}
              </div>
              <h1 className="text-2xl font-bold text-gray-900 mb-1">{job.title}</h1>
              <div className="text-sm text-gray-500">
                <span className="font-medium text-gray-700">{job.company_name}</span>
                {job.location_name && job.location_name !== job.company_name && (
                  <> · {job.location_name}</>
                )}
                {job.city && <> · {job.city}</>}
              </div>
            </div>

            {job.description && (
              <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
                <h2 className="text-sm font-semibold text-gray-900 mb-3">Omschrijving</h2>
                <div className="text-sm text-gray-600 leading-relaxed whitespace-pre-wrap">
                  {job.description}
                </div>
              </div>
            )}

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
                {job.requires_bevoegdheid?.length > 0 && (
                  <div className="flex items-start gap-2">
                    <span className="w-4 h-4 rounded-full flex items-center justify-center text-xs bg-blue-100 text-blue-600 mt-0.5 shrink-0">✓</span>
                    <span className="text-sm text-gray-600">
                      Bevoegdheid vereist: {job.requires_bevoegdheid.join(", ")}
                    </span>
                  </div>
                )}
                {job.min_experience > 0 && (
                  <div className="flex items-center gap-2">
                    <span className="w-4 h-4 rounded-full flex items-center justify-center text-xs bg-blue-100 text-blue-600 shrink-0">✓</span>
                    <span className="text-sm text-gray-600">
                      Minimaal {job.min_experience} jaar werkervaring
                    </span>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Sidebar */}
          <div className="space-y-4">
            {/* CTA */}
            <div className="bg-blue-700 rounded-2xl p-5 text-white">
              <div className="text-sm font-semibold mb-1">Interesse in deze vacature?</div>
              <p className="text-xs text-blue-200 mb-4">
                Je wordt doorgestuurd naar de website van {job.company_name}.
              </p>
              <button
                onClick={handleVisit}
                disabled={redirecting}
                className="w-full block text-center text-sm font-semibold bg-white text-blue-700 rounded-lg py-2.5 hover:bg-blue-50 transition-colors disabled:opacity-60"
              >
                {redirecting ? "Bezig..." : user ? "Bezoek vacature →" : "Registreer & bezoek →"}
              </button>
              {!user && (
                <Link
                  href={`/login?next=/jobs/${id}`}
                  className="block text-center text-xs text-blue-200 hover:text-white mt-2 transition-colors"
                >
                  Al een account? Inloggen
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
                    {job.salary_max && job.salary_max !== job.salary_min && `–€${job.salary_max}`}
                    <span className="text-xs font-normal text-gray-400"> per maand</span>
                  </div>
                </div>
              )}
              {(job.hours_min || job.hours_max) && (
                <div>
                  <div className="text-xs text-gray-400 mb-0.5">Uren</div>
                  <div className="text-sm font-medium text-gray-700">
                    {job.hours_min && job.hours_max && job.hours_min !== job.hours_max
                      ? `${job.hours_min}–${job.hours_max} uur per week`
                      : `${job.hours_min || job.hours_max} uur per week`}
                  </div>
                </div>
              )}
              {job.age_min != null && job.age_max != null && (
                <div>
                  <div className="text-xs text-gray-400 mb-0.5">Leeftijdsgroep</div>
                  <div className="text-sm font-medium text-gray-700">{job.age_min}–{job.age_max} jaar</div>
                </div>
              )}
              {job.contract_type && (
                <div>
                  <div className="text-xs text-gray-400 mb-0.5">Contract</div>
                  <div className="text-sm font-medium text-gray-700">
                    {CONTRACT_LABELS[job.contract_type] || job.contract_type}
                  </div>
                </div>
              )}
              {job.city && (
                <div>
                  <div className="text-xs text-gray-400 mb-0.5">Locatie</div>
                  <div className="text-sm font-medium text-gray-700">
                    {job.location_name || job.city}
                  </div>
                </div>
              )}
              <div>
                <div className="text-xs text-gray-400 mb-0.5">Geplaatst</div>
                <div className="text-sm font-medium text-gray-700">{postedDate}</div>
              </div>
            </div>

            {/* Company card */}
            <div className="bg-white rounded-2xl p-5 shadow-sm border border-gray-100">
              {job.company_logo && (
                <img src={job.company_logo} alt={job.company_name} className="h-8 mb-3 object-contain" />
              )}
              <div className="text-xs text-gray-400 mb-1">Werkgever</div>
              <div className="text-sm font-semibold text-gray-900">{job.company_name}</div>
              {job.location_name && (
                <div className="text-xs text-gray-400 mt-0.5">{job.location_name}</div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

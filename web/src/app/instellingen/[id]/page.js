"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import dynamic from "next/dynamic";
import { api } from "@/lib/api";
import Nav from "@/components/Nav";

const InstitutionMap = dynamic(() => import("@/components/InstitutionMap"), {
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center h-full bg-gray-100">
      <div className="text-gray-400 text-sm">Kaart laden...</div>
    </div>
  ),
});

const TYPE_LABELS = {
  bso: "BSO",
  kdv: "KDV / Kinderdagverblijf",
  gastouder: "Gastouderbureau",
  peuterspeelzaal: "Peuterspeelzaal",
};

const TYPE_COLORS = {
  bso: "bg-blue-100 text-blue-700",
  kdv: "bg-emerald-100 text-emerald-700",
  gastouder: "bg-amber-100 text-amber-700",
  peuterspeelzaal: "bg-purple-100 text-purple-700",
};

const CONTRACT_LABELS = {
  fulltime: "Full-time",
  parttime: "Part-time",
  zzp: "ZZP / Freelance",
  temp: "Tijdelijk",
};

function StarRating({ rating }) {
  return (
    <div className="flex items-center gap-0.5">
      {[1, 2, 3, 4, 5].map((star) => (
        <svg
          key={star}
          className={`w-4 h-4 ${star <= Math.round(rating) ? "text-amber-400" : "text-gray-200"}`}
          fill="currentColor"
          viewBox="0 0 20 20"
        >
          <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
        </svg>
      ))}
    </div>
  );
}

export default function InstitutionDetailPage({ params }) {
  const { id } = params;
  const [institution, setInstitution] = useState(null);
  const [reviews, setReviews] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.institution(id),
      api.reviews(id),
      api.jobs({ institution: id }),
    ])
      .then(([inst, rev, jobData]) => {
        setInstitution(inst);
        setReviews(rev);
        setJobs(jobData.results || jobData);
      })
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

  if (!institution) {
    return (
      <div className="min-h-screen bg-white">
        <Nav />
        <div className="flex flex-col items-center justify-center py-32 gap-4">
          <p className="text-gray-500">Instelling niet gevonden.</p>
          <Link href="/map" className="text-blue-700 hover:underline text-sm">Terug naar kaart</Link>
        </div>
      </div>
    );
  }

  const [lng, lat] = institution.location?.coordinates || [5.2913, 52.1326];

  return (
    <div className="min-h-screen bg-gray-50">
      <Nav />

      <div className="max-w-5xl mx-auto px-4 sm:px-6 py-6 sm:py-8">
        {/* Breadcrumb */}
        <div className="flex items-center gap-2 text-sm text-gray-400 mb-6">
          <Link href="/map" className="hover:text-blue-700 transition-colors">Kaart</Link>
          <span>/</span>
          <span className="text-gray-600">{institution.name}</span>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main content */}
          <div className="lg:col-span-2 space-y-6">
            {/* Header card */}
            <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className={`text-xs font-semibold px-2.5 py-1 rounded-full ${TYPE_COLORS[institution.institution_type] || "bg-gray-100 text-gray-600"}`}>
                    {TYPE_LABELS[institution.institution_type] || institution.institution_type}
                  </span>
                  {institution.lrk_verified && (
                    <span className="flex items-center gap-1 text-xs text-green-600 font-medium bg-green-50 px-2.5 py-1 rounded-full">
                      ✓ LRK geregistreerd
                    </span>
                  )}
                  {institution.is_claimed && (
                    <span className="text-xs text-blue-600 font-medium bg-blue-50 px-2.5 py-1 rounded-full">
                      Beheerd profiel
                    </span>
                  )}
                </div>
                {institution.avg_rating && (
                  <div className="flex items-center gap-1.5 shrink-0">
                    <StarRating rating={institution.avg_rating} />
                    <span className="text-sm font-semibold text-gray-700">{institution.avg_rating}</span>
                  </div>
                )}
              </div>
              <h1 className="text-2xl font-bold text-gray-900 mb-1">{institution.name}</h1>
              <p className="text-sm text-gray-500">
                {institution.street} {institution.house_number}, {institution.postcode} {institution.city}
                {institution.province && ` · ${institution.province}`}
              </p>

              {institution.description && (
                <p className="mt-4 text-sm text-gray-600 leading-relaxed">{institution.description}</p>
              )}
            </div>

            {/* Details grid */}
            <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
              <h2 className="text-sm font-semibold text-gray-900 mb-4">Informatie</h2>
              <div className="grid grid-cols-2 gap-4">
                {institution.capacity && (
                  <div>
                    <div className="text-xs text-gray-400 mb-0.5">Capaciteit</div>
                    <div className="text-sm font-medium text-gray-700">{institution.capacity} kinderen</div>
                  </div>
                )}
                {institution.available_spots != null && (
                  <div>
                    <div className="text-xs text-gray-400 mb-0.5">Beschikbare plekken</div>
                    <div className="text-sm font-medium text-gray-700">{institution.available_spots}</div>
                  </div>
                )}
                {institution.lrk_number && (
                  <div>
                    <div className="text-xs text-gray-400 mb-0.5">LRK-nummer</div>
                    <div className="text-sm font-medium text-gray-700 font-mono">{institution.lrk_number}</div>
                  </div>
                )}
                {institution.phone && (
                  <div>
                    <div className="text-xs text-gray-400 mb-0.5">Telefoon</div>
                    <a href={`tel:${institution.phone}`} className="text-sm font-medium text-blue-700 hover:underline">
                      {institution.phone}
                    </a>
                  </div>
                )}
                {institution.email && (
                  <div>
                    <div className="text-xs text-gray-400 mb-0.5">E-mail</div>
                    <a href={`mailto:${institution.email}`} className="text-sm font-medium text-blue-700 hover:underline">
                      {institution.email}
                    </a>
                  </div>
                )}
                {institution.website && (
                  <div>
                    <div className="text-xs text-gray-400 mb-0.5">Website</div>
                    <a
                      href={institution.website}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sm font-medium text-blue-700 hover:underline"
                    >
                      {institution.website.replace(/^https?:\/\//, "")}
                    </a>
                  </div>
                )}
              </div>

              {institution.opening_hours && (
                <div className="mt-4 pt-4 border-t border-gray-50">
                  <div className="text-xs text-gray-400 mb-2">Openingstijden</div>
                  <pre className="text-sm text-gray-600 whitespace-pre-wrap font-sans leading-relaxed">
                    {institution.opening_hours}
                  </pre>
                </div>
              )}
            </div>

            {/* Jobs at this institution */}
            {jobs.length > 0 && (
              <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
                <h2 className="text-sm font-semibold text-gray-900 mb-4">
                  Vacatures ({jobs.length})
                </h2>
                <div className="space-y-3">
                  {jobs.map((job) => (
                    <Link
                      key={job.id}
                      href={`/jobs/${job.id}`}
                      className="flex items-center justify-between p-3 rounded-xl border border-gray-100 hover:border-blue-200 hover:bg-blue-50 transition-colors group"
                    >
                      <div>
                        <div className="text-sm font-medium text-gray-900 group-hover:text-blue-700 transition-colors">
                          {job.title}
                        </div>
                        <div className="text-xs text-gray-400 mt-0.5">
                          {CONTRACT_LABELS[job.contract_type] || job.contract_type}
                          {job.hours_per_week && ` · ${job.hours_per_week} uur/week`}
                        </div>
                      </div>
                      {(job.salary_min || job.salary_max) && (
                        <div className="text-sm font-medium text-gray-600 shrink-0 ml-4">
                          €{job.salary_min}
                          {job.salary_max && job.salary_max !== job.salary_min && `–${job.salary_max}`}
                          /u
                        </div>
                      )}
                    </Link>
                  ))}
                </div>
              </div>
            )}

            {/* Organisatiestructuur (moeder-dochter) */}
            {(institution.parent_info || (institution.locations && institution.locations.length > 0)) && (
              <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
                {institution.parent_info && (
                  <div className="mb-4 flex items-center gap-2 text-sm text-gray-500">
                    <span>Onderdeel van</span>
                    <Link
                      href={`/instellingen/${institution.parent_info.id}`}
                      className="font-semibold text-blue-700 hover:underline"
                    >
                      {institution.parent_info.naam_houder || institution.parent_info.name}
                    </Link>
                  </div>
                )}

                {institution.locations && institution.locations.length > 0 && (
                  <>
                    <h2 className="text-sm font-semibold text-gray-900 mb-3">
                      {institution.parent_info ? "Andere locaties" : "Locaties"}{" "}
                      <span className="text-gray-400 font-normal">({institution.locations.length})</span>
                    </h2>
                    <div className="space-y-2">
                      {institution.locations.map((loc) => (
                        <Link
                          key={loc.id}
                          href={`/instellingen/${loc.id}`}
                          className="flex items-center justify-between p-3 rounded-xl border border-gray-100 hover:border-blue-200 hover:bg-blue-50 transition-colors group"
                        >
                          <div>
                            <div className="text-sm font-medium text-gray-900 group-hover:text-blue-700 transition-colors">
                              {loc.name}
                            </div>
                            <div className="text-xs text-gray-400 mt-0.5">
                              {loc.city} · {TYPE_LABELS[loc.institution_type] || loc.institution_type}
                            </div>
                          </div>
                          {loc.active_job_count > 0 && (
                            <span className="shrink-0 ml-3 text-xs font-semibold bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full">
                              {loc.active_job_count} vacature{loc.active_job_count !== 1 ? "s" : ""}
                            </span>
                          )}
                        </Link>
                      ))}
                    </div>
                  </>
                )}
              </div>
            )}

            {/* Reviews */}
            <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
              <h2 className="text-sm font-semibold text-gray-900 mb-4">
                Beoordelingen {reviews.length > 0 && `(${reviews.length})`}
              </h2>
              {reviews.length === 0 ? (
                <p className="text-sm text-gray-400">Nog geen beoordelingen.</p>
              ) : (
                <div className="space-y-4">
                  {reviews.map((review) => (
                    <div key={review.id} className="border-b border-gray-50 pb-4 last:border-0 last:pb-0">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-sm font-medium text-gray-700">{review.author_name}</span>
                        <StarRating rating={review.rating} />
                      </div>
                      {review.text && (
                        <p className="text-sm text-gray-500 leading-relaxed">{review.text}</p>
                      )}
                      <span className="text-xs text-gray-300 mt-1 block">
                        {new Date(review.created_at).toLocaleDateString("nl-NL")}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Sidebar */}
          <div className="space-y-4">
            {/* Mini map */}
            <div className="bg-white rounded-2xl overflow-hidden shadow-sm border border-gray-100 h-48">
              <InstitutionMap
                institutions={[institution]}
                initialViewState={{ longitude: lng, latitude: lat, zoom: 14 }}
              />
            </div>

            {/* Quick info */}
            <div className="bg-white rounded-2xl p-5 shadow-sm border border-gray-100 space-y-3">
              <div className="text-xs text-gray-400 font-medium uppercase tracking-wide">Adres</div>
              <div className="text-sm text-gray-700 leading-relaxed">
                {institution.street} {institution.house_number}<br />
                {institution.postcode} {institution.city}
              </div>
              <a
                href={`https://maps.google.com/?q=${encodeURIComponent(`${institution.street} ${institution.house_number}, ${institution.city}`)}`}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-block text-xs text-blue-700 hover:underline"
              >
                Open in Google Maps →
              </a>
            </div>

            {/* CTA */}
            <div className="bg-blue-700 rounded-2xl p-5 text-white">
              <div className="text-sm font-semibold mb-1">Werken bij {institution.name}?</div>
              <div className="text-xs text-blue-200 mb-3 leading-relaxed">
                Bekijk openstaande vacatures of meld je aan als medewerker.
              </div>
              <Link
                href={`/jobs?institution=${id}`}
                className="block text-center text-xs font-semibold bg-white text-blue-700 rounded-lg py-2 hover:bg-blue-50 transition-colors"
              >
                Bekijk vacatures
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

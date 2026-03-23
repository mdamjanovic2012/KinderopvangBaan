"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import Nav from "@/components/Nav";
import { api } from "@/lib/api";

const CONTRACT_LABELS = {
  fulltime: "Full-time",
  parttime: "Part-time",
  zzp: "ZZP",
  temp: "Tijdelijk",
};

const STATUS_COLORS = {
  active: "bg-green-50 text-green-600",
  inactive: "bg-gray-100 text-gray-500",
};

export default function MyVacaturesPage() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!authLoading && !user) router.push("/login");
    if (!authLoading && user && user.role !== "institution") router.push("/dashboard");
  }, [user, authLoading, router]);

  useEffect(() => {
    if (!user) return;
    api.jobs()
      .then((data) => {
        const all = data.results || data;
        // Filter to only this user's institution jobs - backend filters by posted_by implicitly for institution role
        setJobs(all);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [user]);

  if (authLoading || loading) {
    return (
      <div className="min-h-screen bg-white"><Nav />
        <div className="flex items-center justify-center py-32 text-gray-400">Laden...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Nav />
      <div className="max-w-4xl mx-auto px-6 py-10">
        <div className="flex items-center gap-3 mb-8">
          <Link href="/dashboard" className="text-xs text-gray-400 hover:text-gray-600">← Dashboard</Link>
          <span className="text-xs text-gray-200">/</span>
          <span className="text-xs text-gray-500">Mijn vacatures</span>
        </div>

        <div className="flex items-center justify-between mb-6">
          <h1 className="text-xl font-bold text-gray-900">Mijn vacatures</h1>
          <Link
            href="/dashboard/vacatures/nieuw"
            className="bg-blue-700 text-white text-sm font-semibold px-4 py-2 rounded-lg hover:bg-blue-800 transition-colors"
          >
            + Nieuwe vacature
          </Link>
        </div>

        {jobs.length === 0 ? (
          <div className="bg-white rounded-2xl p-12 border border-gray-100 shadow-sm text-center">
            <div className="text-4xl mb-3">📋</div>
            <p className="text-gray-500 font-medium mb-1">Geen vacatures</p>
            <p className="text-sm text-gray-400 mb-6">Plaats je eerste vacature om medewerkers te vinden.</p>
            <Link
              href="/dashboard/vacatures/nieuw"
              className="inline-block bg-blue-700 text-white text-sm font-semibold px-5 py-2 rounded-lg hover:bg-blue-800 transition-colors"
            >
              Vacature plaatsen
            </Link>
          </div>
        ) : (
          <div className="space-y-3">
            {jobs.map((job) => (
              <div
                key={job.id}
                className="bg-white rounded-2xl p-5 border border-gray-100 shadow-sm flex items-center justify-between gap-4"
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${job.is_active ? STATUS_COLORS.active : STATUS_COLORS.inactive}`}>
                      {job.is_active ? "Actief" : "Inactief"}
                    </span>
                    <span className="text-xs text-gray-400">
                      {CONTRACT_LABELS[job.contract_type] || job.contract_type}
                    </span>
                    {job.is_premium && (
                      <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-yellow-50 text-yellow-600">Uitgelicht</span>
                    )}
                  </div>
                  <div className="font-semibold text-gray-900 truncate">{job.title}</div>
                  <div className="text-xs text-gray-400 mt-0.5">
                    {job.institution_city}
                    {job.hours_per_week && ` · ${job.hours_per_week} uur/week`}
                    {(job.salary_min || job.salary_max) && ` · €${job.salary_min}–${job.salary_max}/u`}
                  </div>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <Link
                    href={`/jobs/${job.id}`}
                    className="text-xs text-gray-400 hover:text-blue-700 transition-colors px-3 py-1.5 rounded-lg border border-gray-200 hover:border-blue-200"
                  >
                    Bekijken
                  </Link>
                  <Link
                    href={`/dashboard/vacatures/${job.id}/bewerken`}
                    className="text-xs text-blue-700 font-medium hover:text-blue-800 transition-colors px-3 py-1.5 rounded-lg border border-blue-200 hover:bg-blue-50"
                  >
                    Bewerken
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

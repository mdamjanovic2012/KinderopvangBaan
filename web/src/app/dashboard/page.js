"use client";

import { useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import Nav from "@/components/Nav";

const ROLE_CONFIG = {
  worker: {
    title: "Welkom terug",
    subtitle: "Vind vacatures die bij jou passen.",
    actions: [
      { href: "/jobs", label: "Bekijk vacatures", icon: "📋", primary: true },
      { href: "/dashboard/profiel", label: "Mijn profiel", icon: "👤", primary: false },
    ],
  },
  institution: {
    title: "Welkom terug",
    subtitle: "Beheer je instelling en vacatures.",
    actions: [
      { href: "/dashboard/vacatures/nieuw", label: "Vacature plaatsen", icon: "➕", primary: true },
      { href: "/dashboard/vacatures", label: "Mijn vacatures", icon: "📋", primary: false },
      { href: "/dashboard/instelling", label: "Instellingsprofiel", icon: "🏫", primary: false },
    ],
  },
  parent: {
    title: "Welkom terug",
    subtitle: "Zoek de beste kinderopvang bij jou in de buurt.",
    actions: [
      { href: "/map", label: "Kaart bekijken", icon: "🗺️", primary: true },
      { href: "/jobs", label: "Vacatures", icon: "📋", primary: false },
    ],
  },
};

export default function DashboardPage() {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) {
      router.push("/login");
    }
  }, [user, loading, router]);

  if (loading || !user) {
    return (
      <div className="min-h-screen bg-white">
        <Nav />
        <div className="flex items-center justify-center py-32 text-gray-400">Laden...</div>
      </div>
    );
  }

  const config = ROLE_CONFIG[user.role] || ROLE_CONFIG.worker;

  return (
    <div className="min-h-screen bg-gray-50">
      <Nav />

      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-8 sm:py-12">
        {/* Greeting */}
        <div className="mb-10">
          <div className="flex items-center gap-4 mb-2">
            <div className="w-12 h-12 rounded-full bg-blue-100 flex items-center justify-center text-blue-700 font-bold text-xl">
              {(user.first_name || user.username)?.[0]?.toUpperCase()}
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                {config.title}, {user.first_name || user.username}!
              </h1>
              <p className="text-sm text-gray-400">{config.subtitle}</p>
            </div>
          </div>
        </div>

        {/* Actions grid */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-10">
          {config.actions.map((action) => (
            <Link
              key={action.href}
              href={action.href}
              className={`flex flex-col items-center justify-center gap-3 p-6 rounded-2xl border transition-all group ${
                action.primary
                  ? "bg-blue-700 border-blue-700 text-white hover:bg-blue-800 shadow-lg shadow-blue-200"
                  : "bg-white border-gray-100 text-gray-700 hover:border-blue-200 hover:shadow-md shadow-sm"
              }`}
            >
              <span className="text-3xl">{action.icon}</span>
              <span className={`text-sm font-semibold text-center ${action.primary ? "text-white" : "text-gray-900 group-hover:text-blue-700"} transition-colors`}>
                {action.label}
              </span>
            </Link>
          ))}
        </div>

        {/* Info card */}
        <div className="bg-white rounded-2xl p-6 border border-gray-100 shadow-sm">
          <h2 className="text-sm font-semibold text-gray-900 mb-4">Accountgegevens</h2>
          <div className="grid grid-cols-2 gap-4">
            {(user.first_name || user.last_name) && (
              <div className="col-span-2">
                <div className="text-xs text-gray-400 mb-0.5">Naam</div>
                <div className="text-sm font-medium text-gray-700">
                  {[user.first_name, user.last_name].filter(Boolean).join(" ")}
                </div>
              </div>
            )}
            <div>
              <div className="text-xs text-gray-400 mb-0.5">Gebruikersnaam</div>
              <div className="text-sm font-medium text-gray-700">{user.username}</div>
            </div>
            <div>
              <div className="text-xs text-gray-400 mb-0.5">E-mailadres</div>
              <div className="text-sm font-medium text-gray-700">{user.email || "—"}</div>
            </div>
            <div>
              <div className="text-xs text-gray-400 mb-0.5">Accounttype</div>
              <div className="text-sm font-medium text-gray-700">
                {user.role === "worker" ? "Pedagogisch medewerker" : user.role === "institution" ? "Instelling" : "—"}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

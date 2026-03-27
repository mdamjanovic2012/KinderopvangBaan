"use client";

import Link from "next/link";
import { useRouter, usePathname } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { useState, useEffect } from "react";

const ROLE_LABELS = {
  worker: "Medewerker",
  institution: "Instelling",
  parent: "Ouder",
};

export default function Nav() {
  const { user, logout, loading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    setMenuOpen(false);
  }, [pathname]);

  const handleLogout = () => {
    logout();
    router.push("/");
  };

  return (
    <nav className="border-b border-gray-100 bg-white">
      <div className="flex items-center justify-between px-4 sm:px-8 py-4">
        <Link href="/" className="flex items-center gap-1">
          <span className="text-xl font-bold text-blue-700">KinderopvangBaan</span>
          <span className="text-xs text-gray-400 font-medium">.nl</span>
        </Link>

        {/* Desktop nav */}
        <div className="hidden sm:flex items-center gap-6 text-sm font-medium text-gray-600">
          <Link href="/map" className="hover:text-blue-700 transition-colors">Kaart</Link>
          <Link href="/jobs" className="hover:text-blue-700 transition-colors">Vacatures</Link>
          <Link href="/workers" className="hover:text-blue-700 transition-colors">Medewerkers</Link>
          <Link href="/diplomacheck" className="hover:text-blue-700 transition-colors">Diplomacheck</Link>

          {!loading && (
            user ? (
              <div className="flex items-center gap-3">
                <Link href="/dashboard" className="flex items-center gap-2 hover:text-blue-700 transition-colors">
                  <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center text-blue-700 font-semibold text-sm">
                    {user.username?.[0]?.toUpperCase()}
                  </div>
                  <div className="flex flex-col leading-none">
                    <span className="text-gray-900 font-medium text-sm">{user.username}</span>
                    <span className="text-xs text-gray-400">{ROLE_LABELS[user.role] || user.role}</span>
                  </div>
                </Link>
                <button onClick={handleLogout} className="text-sm text-gray-400 hover:text-gray-700 transition-colors">
                  Uitloggen
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-3">
                <Link href="/login" className="hover:text-blue-700 transition-colors">Inloggen</Link>
                <Link href="/register" className="bg-blue-700 text-white px-4 py-2 rounded-lg hover:bg-blue-800 transition-colors">
                  Registreren
                </Link>
              </div>
            )
          )}
        </div>

        {/* Mobile hamburger */}
        <button
          className="sm:hidden p-2 rounded-lg text-gray-500 hover:bg-gray-100 transition-colors"
          onClick={() => setMenuOpen((o) => !o)}
          aria-label="Menu openen"
        >
          {menuOpen ? (
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          ) : (
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          )}
        </button>
      </div>

      {/* Mobile menu dropdown */}
      {menuOpen && (
        <div className="sm:hidden border-t border-gray-100 px-4 py-3 bg-white">
          <div className="space-y-1">
            <Link href="/map" className="block py-2.5 text-sm font-medium text-gray-700 hover:text-blue-700 transition-colors">Kaart</Link>
            <Link href="/jobs" className="block py-2.5 text-sm font-medium text-gray-700 hover:text-blue-700 transition-colors">Vacatures</Link>
            <Link href="/workers" className="block py-2.5 text-sm font-medium text-gray-700 hover:text-blue-700 transition-colors">Medewerkers</Link>
            <Link href="/diplomacheck" className="block py-2.5 text-sm font-medium text-gray-700 hover:text-blue-700 transition-colors">Diplomacheck</Link>
          </div>

          {!loading && (
            user ? (
              <div className="pt-3 mt-3 border-t border-gray-100 space-y-1">
                <Link href="/dashboard" className="flex items-center gap-2 py-2">
                  <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center text-blue-700 font-semibold text-sm shrink-0">
                    {user.username?.[0]?.toUpperCase()}
                  </div>
                  <div className="flex flex-col leading-none">
                    <span className="text-gray-900 font-medium text-sm">{user.username}</span>
                    <span className="text-xs text-gray-400">{ROLE_LABELS[user.role] || user.role}</span>
                  </div>
                </Link>
                <button onClick={handleLogout} className="block w-full text-left py-2 text-sm text-gray-400 hover:text-gray-700 transition-colors">
                  Uitloggen
                </button>
              </div>
            ) : (
              <div className="pt-3 mt-3 border-t border-gray-100 space-y-2">
                <Link href="/login" className="block py-2.5 text-sm font-medium text-gray-700 hover:text-blue-700 transition-colors">Inloggen</Link>
                <Link href="/register" className="block text-center bg-blue-700 text-white px-4 py-2.5 rounded-lg hover:bg-blue-800 transition-colors text-sm font-semibold">
                  Registreren
                </Link>
              </div>
            )
          )}
        </div>
      )}
    </nav>
  );
}

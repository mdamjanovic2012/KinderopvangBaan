"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";

const ROLE_LABELS = {
  worker: "Medewerker",
  institution: "Instelling",
  parent: "Ouder",
};

export default function Nav() {
  const { user, logout, loading } = useAuth();
  const router = useRouter();

  const handleLogout = () => {
    logout();
    router.push("/");
  };

  return (
    <nav className="flex items-center justify-between px-8 py-4 border-b border-gray-100 bg-white">
      <Link href="/" className="flex items-center gap-1">
        <span className="text-xl font-bold text-blue-700">KinderopvangBaan</span>
        <span className="text-xs text-gray-400 font-medium">.nl</span>
      </Link>

      <div className="flex items-center gap-6 text-sm font-medium text-gray-600">
        <Link href="/map" className="hover:text-blue-700 transition-colors">Kaart</Link>
        <Link href="/jobs" className="hover:text-blue-700 transition-colors">Vacatures</Link>
        <Link href="/workers" className="hover:text-blue-700 transition-colors">Medewerkers</Link>

        {!loading && (
          user ? (
            <div className="flex items-center gap-3">
              <Link
                href="/dashboard"
                className="flex items-center gap-2 hover:text-blue-700 transition-colors"
              >
                <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center text-blue-700 font-semibold text-sm">
                  {user.username?.[0]?.toUpperCase()}
                </div>
                <div className="flex flex-col leading-none">
                  <span className="text-gray-900 font-medium text-sm">{user.username}</span>
                  <span className="text-xs text-gray-400">{ROLE_LABELS[user.role] || user.role}</span>
                </div>
              </Link>
              <button
                onClick={handleLogout}
                className="text-sm text-gray-400 hover:text-gray-700 transition-colors"
              >
                Uitloggen
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-3">
              <Link href="/login" className="hover:text-blue-700 transition-colors">
                Inloggen
              </Link>
              <Link
                href="/register"
                className="bg-blue-700 text-white px-4 py-2 rounded-lg hover:bg-blue-800 transition-colors"
              >
                Registreren
              </Link>
            </div>
          )
        )}
      </div>
    </nav>
  );
}

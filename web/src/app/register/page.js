"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";

const ROLE_OPTIONS = [
  {
    value: "worker",
    label: "Pedagogisch medewerker",
    desc: "Ik zoek een baan in de kinderopvang",
    icon: "👤",
  },
  {
    value: "institution",
    label: "Instelling / Werkgever",
    desc: "Ik wil vacatures plaatsen en medewerkers vinden",
    icon: "🏫",
  },
  {
    value: "parent",
    label: "Ouder",
    desc: "Ik zoek kinderopvang voor mijn kind",
    icon: "👨‍👧",
  },
];

export default function RegisterPage() {
  const { register } = useAuth();
  const router = useRouter();

  const [step, setStep] = useState(1); // 1 = role, 2 = details
  const [form, setForm] = useState({
    role: "",
    username: "",
    email: "",
    password: "",
    passwordConfirm: "",
  });
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleRoleSelect = (role) => {
    setForm((f) => ({ ...f, role }));
    setStep(2);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    if (form.password !== form.passwordConfirm) {
      setError("Wachtwoorden komen niet overeen.");
      return;
    }

    setLoading(true);
    try {
      await register({
        username: form.username,
        email: form.email,
        password: form.password,
        role: form.role,
      });
      router.push("/dashboard");
    } catch (err) {
      const messages = Object.values(err || {}).flat();
      setError(messages[0] || "Registratie mislukt.");
    } finally {
      setLoading(false);
    }
  };

  const selectedRole = ROLE_OPTIONS.find((r) => r.value === form.role);

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <div className="px-4 sm:px-8 py-4 sm:py-5 border-b border-gray-100 bg-white">
        <Link href="/" className="text-xl font-bold text-blue-700">
          KinderopvangBaan<span className="text-gray-400 font-medium text-xs">.nl</span>
        </Link>
      </div>

      <div className="flex flex-1 items-center justify-center px-4 py-16">
        <div className="w-full max-w-md">
          {step === 1 && (
            <div>
              <h1 className="text-xl font-bold text-gray-900 mb-1 text-center">Maak een account aan</h1>
              <p className="text-sm text-gray-400 text-center mb-8">
                Wie ben jij?
              </p>

              <div className="space-y-3">
                {ROLE_OPTIONS.map((option) => (
                  <button
                    key={option.value}
                    onClick={() => handleRoleSelect(option.value)}
                    className="w-full flex items-center gap-4 bg-white rounded-2xl p-5 border border-gray-100 shadow-sm hover:border-blue-200 hover:shadow-md transition-all text-left group"
                  >
                    <span className="text-3xl">{option.icon}</span>
                    <div>
                      <div className="font-semibold text-gray-900 group-hover:text-blue-700 transition-colors">
                        {option.label}
                      </div>
                      <div className="text-sm text-gray-400 mt-0.5">{option.desc}</div>
                    </div>
                    <span className="ml-auto text-gray-200 group-hover:text-blue-300 transition-colors text-lg">→</span>
                  </button>
                ))}
              </div>

              <p className="text-center text-sm text-gray-400 mt-6">
                Al een account?{" "}
                <Link href="/login" className="text-blue-700 hover:underline">
                  Inloggen
                </Link>
              </p>
            </div>
          )}

          {step === 2 && (
            <div className="bg-white rounded-2xl p-8 shadow-sm border border-gray-100">
              <button
                onClick={() => setStep(1)}
                className="flex items-center gap-1 text-xs text-gray-400 hover:text-gray-600 transition-colors mb-6"
              >
                ← Terug
              </button>

              <div className="flex items-center gap-3 mb-6 pb-6 border-b border-gray-50">
                <span className="text-2xl">{selectedRole?.icon}</span>
                <div>
                  <div className="font-semibold text-gray-900 text-sm">{selectedRole?.label}</div>
                  <div className="text-xs text-gray-400">{selectedRole?.desc}</div>
                </div>
              </div>

              <h2 className="text-lg font-bold text-gray-900 mb-6">Jouw gegevens</h2>

              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1.5">
                    Gebruikersnaam
                  </label>
                  <input
                    type="text"
                    value={form.username}
                    onChange={(e) => setForm((f) => ({ ...f, username: e.target.value }))}
                    required
                    autoFocus
                    autoComplete="username"
                    className="w-full border border-gray-200 rounded-lg px-3 py-2.5 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-200 focus:border-blue-400"
                    placeholder="jouwgebruikersnaam"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1.5">
                    E-mailadres
                  </label>
                  <input
                    type="email"
                    value={form.email}
                    onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
                    required
                    autoComplete="email"
                    className="w-full border border-gray-200 rounded-lg px-3 py-2.5 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-200 focus:border-blue-400"
                    placeholder="jouw@email.nl"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1.5">
                    Wachtwoord
                  </label>
                  <input
                    type="password"
                    value={form.password}
                    onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
                    required
                    minLength={8}
                    autoComplete="new-password"
                    className="w-full border border-gray-200 rounded-lg px-3 py-2.5 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-200 focus:border-blue-400"
                    placeholder="Minimaal 8 tekens"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1.5">
                    Wachtwoord bevestigen
                  </label>
                  <input
                    type="password"
                    value={form.passwordConfirm}
                    onChange={(e) => setForm((f) => ({ ...f, passwordConfirm: e.target.value }))}
                    required
                    autoComplete="new-password"
                    className="w-full border border-gray-200 rounded-lg px-3 py-2.5 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-200 focus:border-blue-400"
                    placeholder="••••••••"
                  />
                </div>

                {error && (
                  <div className="text-xs text-red-600 bg-red-50 border border-red-100 rounded-lg px-3 py-2">
                    {error}
                  </div>
                )}

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full bg-blue-700 text-white font-semibold py-2.5 rounded-lg hover:bg-blue-800 transition-colors disabled:opacity-60 disabled:cursor-not-allowed text-sm"
                >
                  {loading ? "Bezig..." : "Account aanmaken"}
                </button>

                <p className="text-xs text-gray-400 text-center">
                  Door te registreren ga je akkoord met onze{" "}
                  <Link href="/voorwaarden" className="text-blue-700 hover:underline">
                    algemene voorwaarden
                  </Link>
                  .
                </p>
              </form>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

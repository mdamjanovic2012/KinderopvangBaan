import Link from "next/link";
import Nav from "@/components/Nav";

export default function Home() {
  return (
    <main className="min-h-screen bg-white">
      <Nav />

      {/* Hero */}
      <section className="flex flex-col items-center justify-center text-center px-6 py-16 sm:py-24 bg-gradient-to-b from-blue-50 to-white">
        <span className="bg-blue-100 text-blue-700 text-xs font-semibold px-3 py-1 rounded-full mb-6">
          Specialist in kinderopvang
        </span>
        <h1 className="text-3xl sm:text-5xl font-bold text-gray-900 max-w-3xl leading-tight mb-4">
          Vind vacatures zo dicht mogelijk{" "}
          <span className="text-blue-700">bij huis</span>
        </h1>
        <p className="text-base sm:text-lg text-gray-600 max-w-xl mb-2">
          Alleen voor loondienst binnen de kinderopvang cao
        </p>
        <p className="text-sm sm:text-base text-green-600 font-semibold mb-10">
          Volledig gratis voor werkzoekenden en werkgevers
        </p>
        <div className="flex flex-col sm:flex-row gap-3 w-full sm:w-auto">
          <Link
            href="/jobs"
            className="bg-blue-700 text-white px-6 py-3 sm:px-8 sm:py-4 rounded-xl font-semibold sm:text-lg hover:bg-blue-800 transition-colors shadow-lg shadow-blue-200 text-center"
          >
            Zoek vacatures
          </Link>
          <Link
            href="/dashboard/vacatures/nieuw"
            className="border border-blue-700 text-blue-700 px-6 py-3 sm:px-8 sm:py-4 rounded-xl font-semibold sm:text-lg hover:bg-blue-50 transition-colors text-center"
          >
            Plaats gratis vacature
          </Link>
        </div>
      </section>

      {/* Gratis badge */}
      <section className="bg-green-50 border-y border-green-100 py-10 px-6">
        <div className="max-w-4xl mx-auto grid grid-cols-1 sm:grid-cols-3 gap-6 text-center">
          {[
            {
              icon: "🎉",
              text: "Volledig gratis en ruim aanbod voor werkzoekenden",
            },
            {
              icon: "✅",
              text: "Vacatures plaatsen is volledig gratis",
            },
            {
              icon: "⚡",
              text: "Heb je al vacatures? Wij zetten ze voor je live in minuten.",
            },
          ].map((item) => (
            <div key={item.text} className="flex flex-col items-center gap-2">
              <span className="text-3xl">{item.icon}</span>
              <p className="text-sm sm:text-base font-medium text-green-800">
                {item.text}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* Waarom wij bestaan */}
      <section className="py-16 sm:py-24 px-6 bg-white">
        <div className="max-w-4xl mx-auto flex flex-col lg:flex-row gap-12 items-center">
          <div className="flex-1">
            <span className="text-blue-700 font-semibold text-sm uppercase tracking-wide mb-3 block">
              Ons verhaal
            </span>
            <h2 className="text-2xl sm:text-3xl font-bold text-gray-900 mb-6 leading-snug">
              Wij lossen het personeelstekort in de kinderopvang op
            </h2>
            <ul className="space-y-4 text-gray-600 text-sm sm:text-base">
              {[
                "Kinderopvang kampt met een groot personeelstekort — wij helpen dat op te lossen",
                "Werkzoekenden vinden snel een plek dichtbij huis",
                "Organisaties krijgen gratis zichtbaarheid bij de juiste doelgroep",
                "Alles gratis en laagdrempelig — geen verborgen kosten",
              ].map((item) => (
                <li key={item} className="flex items-start gap-3">
                  <span className="text-blue-600 mt-1">✓</span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>
            <Link
              href="/over-ons"
              className="inline-block mt-8 bg-blue-700 text-white px-6 py-3 rounded-xl font-semibold hover:bg-blue-800 transition-colors"
            >
              Waarom wij bestaan
            </Link>
          </div>
          <div className="flex-1 grid grid-cols-2 gap-4">
            {[
              { number: "14.000+", label: "Kinderopvanglocaties in NL" },
              { number: "100%", label: "Gratis voor iedereen" },
              { number: "3 typen", label: "BSO · KDV · Gastouder" },
              { number: "Direct", label: "Vacature live in minuten" },
            ].map((s) => (
              <div
                key={s.label}
                className="bg-blue-50 rounded-2xl p-6 text-center"
              >
                <div className="text-2xl sm:text-3xl font-bold text-blue-700 mb-1">
                  {s.number}
                </div>
                <div className="text-xs sm:text-sm text-gray-500">
                  {s.label}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Werkgevers sectie */}
      <section className="bg-blue-700 py-16 sm:py-24 px-6 text-white">
        <div className="max-w-4xl mx-auto flex flex-col lg:flex-row gap-12 items-center">
          <div className="flex-1">
            <span className="text-blue-200 font-semibold text-sm uppercase tracking-wide mb-3 block">
              Voor werkgevers
            </span>
            <h2 className="text-2xl sm:text-3xl font-bold mb-6 leading-snug">
              Bereik de juiste professionals — gratis
            </h2>
            <ul className="space-y-3 text-blue-100 text-sm sm:text-base mb-8">
              {[
                "Vacatures gratis plaatsen — geen kosten",
                "Bereik specifieke doelgroep binnen kinderopvang",
                "Vacatures snel en eenvoudig online",
                "Werkenbij-pagina? Wij nemen vacatures voor je over",
              ].map((item) => (
                <li key={item} className="flex items-start gap-3">
                  <span className="text-blue-300 mt-1">✓</span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>
            <Link
              href="/register"
              className="inline-block bg-white text-blue-700 px-6 py-3 rounded-xl font-semibold hover:bg-blue-50 transition-colors"
            >
              Gratis vacature plaatsen
            </Link>
          </div>
          <div className="flex-1 bg-blue-800 rounded-2xl p-8 text-center">
            <div className="text-5xl mb-4">🏫</div>
            <h3 className="text-xl font-bold mb-2">Al vacatures beschikbaar?</h3>
            <p className="text-blue-200 text-sm mb-6">
              Stuur ons je werkenbij-pagina en wij zetten al je vacatures gratis
              live — zonder dat je iets hoeft te doen.
            </p>
            <Link
              href="/contact"
              className="inline-block border border-white text-white px-5 py-2 rounded-xl font-semibold hover:bg-blue-700 transition-colors text-sm"
            >
              Neem contact op
            </Link>
          </div>
        </div>
      </section>
    </main>
  );
}

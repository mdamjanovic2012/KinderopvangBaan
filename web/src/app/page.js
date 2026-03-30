import Link from "next/link";
import Nav from "@/components/Nav";
import HomeDiplomaCheck from "@/components/HomeDiplomaCheck";

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
          Alleen loondienst · kinderopvang cao · alle grote organisaties
        </p>
        <p className="text-sm sm:text-base text-green-600 font-semibold mb-10">
          Volledig gratis voor werkzoekenden
        </p>
        <div className="flex flex-col sm:flex-row gap-3 w-full sm:w-auto">
          <Link
            href="/jobs"
            className="bg-blue-700 text-white px-6 py-3 sm:px-8 sm:py-4 rounded-xl font-semibold sm:text-lg hover:bg-blue-800 transition-colors shadow-lg shadow-blue-200 text-center"
          >
            Bekijk alle vacatures
          </Link>
          <Link
            href="/map"
            className="border border-blue-700 text-blue-700 px-6 py-3 sm:px-8 sm:py-4 rounded-xl font-semibold sm:text-lg hover:bg-blue-50 transition-colors text-center"
          >
            📍 In mijn buurt zoeken
          </Link>
        </div>
      </section>

      {/* Voordelen voor werkzoekenden */}
      <section className="bg-green-50 border-y border-green-100 py-10 px-6">
        <div className="max-w-4xl mx-auto grid grid-cols-1 sm:grid-cols-3 gap-6 text-center">
          {[
            {
              icon: "📍",
              text: "Vacatures gesorteerd op afstand — dichtbij huis zoeken",
            },
            {
              icon: "🏢",
              text: "Partou, Kinderdam en meer — alle grote organisaties op één plek",
            },
            {
              icon: "✅",
              text: "Altijd up-to-date — automatisch gesynchroniseerd met de werkgevers",
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

      <HomeDiplomaCheck />

      {/* Hoe het werkt */}
      <section className="py-16 sm:py-24 px-6 bg-white">
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-12">
            <span className="text-blue-700 font-semibold text-sm uppercase tracking-wide mb-3 block">
              Hoe het werkt
            </span>
            <h2 className="text-2xl sm:text-3xl font-bold text-gray-900 leading-snug">
              In drie stappen naar jouw nieuwe baan
            </h2>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-8">
            {[
              {
                step: "1",
                title: "Registreer gratis",
                desc: "Maak een profiel aan met jouw functie, diploma en gewenste uren. Duurt minder dan 2 minuten.",
              },
              {
                step: "2",
                title: "Zoek dichtbij huis",
                desc: "Filter op afstand, functie en contractvorm. Bekijk vacatures van Partou, Kinderdam en andere organisaties.",
              },
              {
                step: "3",
                title: "Solliciteer direct",
                desc: "Klik op een vacature en ga direct naar de sollicitatiepagina van de werkgever. Wij leiden je erheen.",
              },
            ].map((item) => (
              <div key={item.step} className="flex flex-col items-center text-center">
                <div className="w-12 h-12 rounded-full bg-blue-700 text-white font-bold text-xl flex items-center justify-center mb-4">
                  {item.step}
                </div>
                <h3 className="font-semibold text-gray-900 mb-2">{item.title}</h3>
                <p className="text-sm text-gray-500 leading-relaxed">{item.desc}</p>
              </div>
            ))}
          </div>
          <div className="text-center mt-10">
            <Link
              href="/register"
              className="inline-block bg-blue-700 text-white px-8 py-3 rounded-xl font-semibold hover:bg-blue-800 transition-colors"
            >
              Gratis registreren →
            </Link>
          </div>
        </div>
      </section>

      {/* Stats */}
      <section className="bg-blue-50 py-12 px-6">
        <div className="max-w-4xl mx-auto grid grid-cols-2 sm:grid-cols-4 gap-6">
          {[
            { number: "500+", label: "Actuele vacatures" },
            { number: "14.000+", label: "Kinderopvanglocaties in NL" },
            { number: "3 typen", label: "BSO · KDV · Gastouder" },
            { number: "100%", label: "Gratis voor werkzoekenden" },
          ].map((s) => (
            <div
              key={s.label}
              className="bg-white rounded-2xl p-6 text-center shadow-sm"
            >
              <div className="text-2xl sm:text-3xl font-bold text-blue-700 mb-1">
                {s.number}
              </div>
              <div className="text-xs sm:text-sm text-gray-500">{s.label}</div>
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
                "Alle vacatures van grote organisaties automatisch bijgehouden",
                "Alles gratis en laagdrempelig — geen verborgen kosten",
              ].map((item) => (
                <li key={item} className="flex items-start gap-3">
                  <span className="text-blue-600 mt-1">✓</span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>
            <Link
              href="/jobs"
              className="inline-block mt-8 bg-blue-700 text-white px-6 py-3 rounded-xl font-semibold hover:bg-blue-800 transition-colors"
            >
              Bekijk vacatures →
            </Link>
          </div>
          <div className="flex-1 bg-blue-700 rounded-2xl p-8 text-white text-center">
            <div className="text-5xl mb-4">🎓</div>
            <h3 className="text-xl font-bold mb-2">Weet jij welk diploma je nodig hebt?</h3>
            <p className="text-blue-200 text-sm mb-6">
              Controleer of jouw diploma geldig is voor BSO of KDV.
              Onze diplomacheck geeft je direct antwoord.
            </p>
            <Link
              href="/diplomacheck"
              className="inline-block bg-white text-blue-700 px-5 py-2 rounded-xl font-semibold hover:bg-blue-50 transition-colors text-sm"
            >
              Doe de diplomacheck
            </Link>
          </div>
        </div>
      </section>
    </main>
  );
}

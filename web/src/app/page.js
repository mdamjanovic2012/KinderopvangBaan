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
        <h1 className="text-3xl sm:text-5xl font-bold text-gray-900 max-w-3xl leading-tight mb-6">
          Vind de perfecte plek in{" "}
          <span className="text-blue-700">kinderopvang</span>
        </h1>
        <p className="text-base sm:text-xl text-gray-500 max-w-2xl mb-10">
          Het platform dat BSO&apos;s, KDV&apos;s en gastouderbureaus verbindt met
          pedagogisch medewerkers. Bekijk de interactieve kaart en ontdek
          vacatures bij jou in de buurt.
        </p>
        <div className="flex flex-col sm:flex-row gap-3 w-full sm:w-auto">
          <Link
            href="/map"
            className="bg-blue-700 text-white px-6 py-3 sm:px-8 sm:py-4 rounded-xl font-semibold sm:text-lg hover:bg-blue-800 transition-colors shadow-lg shadow-blue-200 text-center"
          >
            Bekijk de kaart
          </Link>
          <Link
            href="/jobs"
            className="border border-gray-200 text-gray-700 px-6 py-3 sm:px-8 sm:py-4 rounded-xl font-semibold sm:text-lg hover:bg-gray-50 transition-colors text-center"
          >
            Alle vacatures
          </Link>
        </div>
      </section>

      {/* Stats */}
      <section className="grid grid-cols-3 gap-4 sm:gap-8 max-w-3xl mx-auto py-12 sm:py-16 px-6 sm:px-8 text-center">
        {[
          { number: "14.000+", label: "Kinderopvanglocaties in NL" },
          { number: "3 typen", label: "BSO · KDV · Gastouder" },
          { number: "10 km", label: "Gemiddelde zoekradius" },
        ].map((s) => (
          <div key={s.label}>
            <div className="text-2xl sm:text-3xl font-bold text-blue-700 mb-1">{s.number}</div>
            <div className="text-xs sm:text-sm text-gray-500">{s.label}</div>
          </div>
        ))}
      </section>

      {/* Features */}
      <section className="bg-gray-50 py-14 sm:py-20 px-6 sm:px-8">
        <div className="max-w-5xl mx-auto grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 sm:gap-8">
          {[
            {
              icon: "🗺️",
              title: "Interactieve kaart",
              desc: "Alle kinderopvanglocaties op één kaart. Filter op type, afstand en beschikbaarheid.",
            },
            {
              icon: "📍",
              title: "Vacatures in de buurt",
              desc: "Medewerkers zoeken vacatures op loopafstand. Radius instelbaar per persoon.",
            },
            {
              icon: "✅",
              title: "Geverifieerde profielen",
              desc: "VOG-status, LRK-registratie en diploma's gecontroleerd en zichtbaar.",
            },
          ].map((f) => (
            <div key={f.title} className="bg-white rounded-2xl p-8 shadow-sm border border-gray-100">
              <div className="text-4xl mb-4">{f.icon}</div>
              <h3 className="font-semibold text-gray-900 mb-2 text-lg">{f.title}</h3>
              <p className="text-gray-500 text-sm leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}

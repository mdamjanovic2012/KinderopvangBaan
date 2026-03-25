"use client";

import Link from "next/link";
import Nav from "@/components/Nav";

export default function VoorwaardenPage() {
  return (
    <div className="min-h-screen bg-gray-50">
      <Nav />
      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-10 sm:py-14">
        <div className="mb-8">
          <Link href="/" className="text-xs text-gray-400 hover:text-gray-600">← Terug naar home</Link>
        </div>

        <h1 className="text-2xl font-bold text-gray-900 mb-2">Algemene voorwaarden</h1>
        <p className="text-sm text-gray-400 mb-8">Versie 1.0 — Geldig vanaf 1 april 2026</p>

        <div className="space-y-8 text-sm text-gray-700 leading-relaxed">

          {/* Disclaimer */}
          <section>
            <h2 className="text-base font-semibold text-gray-900 mb-3">1. Disclaimer</h2>
            <div className="space-y-2">
              <p>
                KinderopvangBaan.nl is een gratis vacatureplatform voor de kinderopvangsector. Wij brengen werkzoekenden en instellingen samen, maar zijn zelf geen partij in de arbeidsrelatie die tussen hen tot stand komt.
              </p>
              <p>
                Alle vacatures op dit platform zijn geplaatst door de instellingen zelf. KinderopvangBaan.nl is niet verantwoordelijk voor de juistheid, volledigheid of actualiteit van de geplaatste vacatures.
              </p>
              <p>
                Het gebruik van dit platform is geheel op eigen risico. KinderopvangBaan.nl aanvaardt geen aansprakelijkheid voor schade die voortvloeit uit het gebruik van dit platform of uit de arbeidsrelatie tussen gebruikers.
              </p>
            </div>
          </section>

          {/* Selectieproces */}
          <section>
            <h2 className="text-base font-semibold text-gray-900 mb-3">2. Selectieproces bij de instelling</h2>
            <div className="space-y-2">
              <p>
                KinderopvangBaan.nl faciliteert uitsluitend het leggen van contact tussen werkzoekenden en instellingen. Het volledige selectieproces — inclusief sollicitatiegesprekken, beoordeling, arbeidscontract en indiensttreding — vindt plaats bij en wordt beheerd door de instelling zelf.
              </p>
              <p>
                KinderopvangBaan.nl bemoeit zich niet met het selectieproces en kan niet aansprakelijk worden gesteld voor besluiten die de instelling neemt in het kader van werving en selectie.
              </p>
              <p>
                Instellingen zijn zelf verantwoordelijk voor het naleven van geldende wet- en regelgeving op het gebied van arbeidsrecht, gelijke behandeling en privacybescherming.
              </p>
            </div>
          </section>

          {/* VOG en Diploma */}
          <section>
            <h2 className="text-base font-semibold text-gray-900 mb-3">3. VOG en diploma — controle bij de instelling</h2>
            <div className="space-y-2">
              <p>
                <strong className="text-gray-900">Verklaring Omtrent Gedrag (VOG):</strong> Op grond van de Wet kinderopvang zijn instellingen wettelijk verplicht een geldige VOG te bewaren voor alle medewerkers die werken met kinderen. De verificatie en bewaring van de VOG is uitsluitend de verantwoordelijkheid van de instelling. KinderopvangBaan.nl verifieert geen VOG-documenten.
              </p>
              <p>
                <strong className="text-gray-900">Diploma&apos;s en kwalificaties:</strong> Medewerkers in de kinderopvang moeten voldoen aan de eisen uit het Besluit kwaliteit kinderopvang. Instellingen zijn zelf verantwoordelijk voor het controleren en bewaren van diploma&apos;s en andere kwalificatiedocumenten. KinderopvangBaan.nl verifieert geen diploma&apos;s of kwalificaties.
              </p>
              <p>
                Het aangeven van een VOG of diploma op het profiel op KinderopvangBaan.nl is een zelfverklaring van de werkzoekende. De echtheid hiervan wordt niet door ons gecontroleerd.
              </p>
            </div>
          </section>

          {/* Privacy */}
          <section>
            <h2 className="text-base font-semibold text-gray-900 mb-3">4. Privacy en persoonsgegevens</h2>
            <div className="space-y-2">
              <p>
                KinderopvangBaan.nl verwerkt persoonsgegevens conform de Algemene Verordening Gegevensbescherming (AVG). Wij slaan alleen gegevens op die noodzakelijk zijn voor de werking van het platform.
              </p>
              <p>
                Adresgegevens (postcode, huisnummer) worden uitsluitend gebruikt voor het berekenen van de zoekradius en worden nooit gedeeld met derden of getoond op publieke profielen.
              </p>
              <p>
                Je kunt te allen tijde je account en gegevens laten verwijderen door contact op te nemen via ons contactformulier.
              </p>
            </div>
          </section>

          {/* Gratis gebruik */}
          <section>
            <h2 className="text-base font-semibold text-gray-900 mb-3">5. Gratis gebruik</h2>
            <p>
              Het plaatsen van vacatures en het aanmaken van een profiel is volledig gratis. KinderopvangBaan.nl biedt optioneel een uitgelicht-functie voor vacatures (premium listing) tegen een vergoeding. De tarieven worden duidelijk gecommuniceerd voorafgaand aan aankoop.
            </p>
          </section>

          {/* Toepasselijk recht */}
          <section>
            <h2 className="text-base font-semibold text-gray-900 mb-3">6. Toepasselijk recht</h2>
            <p>
              Op deze voorwaarden en het gebruik van KinderopvangBaan.nl is Nederlands recht van toepassing. Geschillen worden voorgelegd aan de bevoegde rechter in Nederland.
            </p>
          </section>

          {/* Contact */}
          <section className="bg-white rounded-2xl p-6 border border-gray-100">
            <h2 className="text-base font-semibold text-gray-900 mb-2">Contact</h2>
            <p className="text-gray-500">
              Vragen over deze voorwaarden? Neem contact op via{" "}
              <a href="mailto:info@kinderopvangbaan.nl" className="text-blue-700 hover:underline">
                info@kinderopvangbaan.nl
              </a>
            </p>
          </section>

        </div>
      </div>
    </div>
  );
}

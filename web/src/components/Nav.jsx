import Link from "next/link";

export default function Nav() {
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
        <Link
          href="/login"
          className="bg-blue-700 text-white px-4 py-2 rounded-lg hover:bg-blue-800 transition-colors"
        >
          Inloggen
        </Link>
      </div>
    </nav>
  );
}

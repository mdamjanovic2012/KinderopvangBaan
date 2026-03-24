"use client";

import { useState, useEffect, useCallback } from "react";
import Nav from "@/components/Nav";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

async function fetchWorkers(params = {}) {
  const qs = new URLSearchParams(params).toString();
  const res = await fetch(`${BASE_URL}/users/workers/?${qs}`);
  if (!res.ok) return [];
  return res.json();
}

const RADIUS_OPTIONS = [5, 10, 15, 25, 50];

function WorkerCard({ worker }) {
  return (
    <div className="bg-white rounded-2xl p-5 border border-gray-100 shadow-sm hover:border-blue-200 hover:shadow-md transition-all">
      <div className="flex items-start gap-4">
        <div className="w-12 h-12 rounded-full bg-blue-100 flex items-center justify-center text-blue-700 font-bold text-lg shrink-0">
          {worker.username?.[0]?.toUpperCase()}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-1">
            {worker.has_vog && (
              <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-green-50 text-green-600">
                ✓ VOG
              </span>
            )}
            {worker.has_diploma && (
              <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-blue-50 text-blue-600">
                Diploma
              </span>
            )}
            {worker.distance_km != null && (
              <span className="text-xs text-gray-400">{worker.distance_km} km</span>
            )}
          </div>
          <div className="font-semibold text-gray-900">{worker.username}</div>
          {worker.years_experience != null && (
            <div className="text-xs text-gray-400 mt-0.5">
              {worker.years_experience} jaar ervaring
            </div>
          )}
          {worker.bio && (
            <p className="text-sm text-gray-500 mt-2 line-clamp-2 leading-relaxed">{worker.bio}</p>
          )}
          {worker.available_days?.length > 0 && (
            <div className="flex gap-1 mt-2 flex-wrap">
              {worker.available_days.map((day) => (
                <span key={day} className="text-xs px-1.5 py-0.5 bg-gray-100 text-gray-500 rounded">
                  {day.charAt(0).toUpperCase() + day.slice(1)}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function WorkersPage() {
  const [workers, setWorkers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [mode, setMode] = useState("all");
  const [radius, setRadius] = useState(15);
  const [userLocation, setUserLocation] = useState(null);

  const loadAll = useCallback(() => {
    setLoading(true);
    fetchWorkers()
      .then(setWorkers)
      .finally(() => setLoading(false));
  }, []);

  const loadNearby = useCallback(() => {
    if (!userLocation) return;
    setLoading(true);
    fetchWorkers({ lat: userLocation.lat, lng: userLocation.lng, radius })
      .then(setWorkers)
      .finally(() => setLoading(false));
  }, [userLocation, radius]);

  useEffect(() => {
    if (mode === "all") loadAll();
    else loadNearby();
  }, [mode, loadAll, loadNearby]);

  const handleGeolocate = () => {
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setUserLocation({ lat: pos.coords.latitude, lng: pos.coords.longitude });
        setMode("nearby");
      },
      () => alert("Locatie niet beschikbaar.")
    );
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <Nav />

      <div className="bg-white border-b border-gray-100 shadow-sm">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 py-4 flex items-center gap-2 sm:gap-3 flex-wrap">
          <span className="text-sm font-semibold text-gray-700">Medewerkers</span>

          {mode === "nearby" && (
            <select
              value={radius}
              onChange={(e) => setRadius(Number(e.target.value))}
              className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm text-gray-700 bg-white focus:outline-none focus:ring-2 focus:ring-blue-200"
            >
              {RADIUS_OPTIONS.map((r) => (
                <option key={r} value={r}>{r} km</option>
              ))}
            </select>
          )}

          <button
            onClick={handleGeolocate}
            className="flex items-center gap-1.5 bg-blue-700 text-white text-sm font-medium px-4 py-1.5 rounded-lg hover:bg-blue-800 transition-colors"
          >
            📍 In mijn buurt
          </button>

          {mode === "nearby" && (
            <button onClick={() => setMode("all")} className="text-sm text-gray-500 hover:text-gray-700 underline">
              Alles tonen
            </button>
          )}

          <div className="ml-auto text-sm text-gray-400">
            {loading ? "Laden..." : `${workers.length} medewerkers`}
          </div>
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-4 sm:px-6 py-6 sm:py-8">
        <div className="mb-4">
          <h1 className="text-xl font-bold text-gray-900">Beschikbare medewerkers</h1>
          <p className="text-sm text-gray-400 mt-0.5">
            Pedagogisch medewerkers die op zoek zijn naar een functie in de kinderopvang.
          </p>
        </div>

        {!loading && workers.length === 0 && (
          <div className="text-center py-20 text-gray-400">
            <div className="text-4xl mb-3">👤</div>
            <p className="text-sm">Geen medewerkers gevonden.</p>
          </div>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {workers.map((worker) => (
            <WorkerCard key={worker.id} worker={worker} />
          ))}
        </div>
      </div>
    </div>
  );
}

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

function getToken() {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("kb_access");
}

async function request(path, options = {}) {
  const token = getToken();
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers || {}),
    },
  });
  if (!res.ok) throw await res.json();
  return res.json();
}

export const api = {
  get: (path) => request(path),

  // Jobs
  jobMapPins: (params = {}) => {
    const qs = new URLSearchParams(
      Object.fromEntries(Object.entries(params).filter(([, v]) => v !== "" && v != null))
    ).toString();
    return request(`/jobs/map-pins/${qs ? "?" + qs : ""}`);
  },
  jobs: (params = {}) => {
    const qs = new URLSearchParams(
      Object.fromEntries(Object.entries(params).filter(([, v]) => v !== "" && v != null))
    ).toString();
    return request(`/jobs/?${qs}`);
  },
  job: (id) => request(`/jobs/${id}/`),
  nearbyJobs: ({ lat, lng, radius = 15, ...extra } = {}) => {
    const params = new URLSearchParams({ lat, lng, radius });
    Object.entries(extra).forEach(([k, v]) => { if (v !== "" && v != null) params.set(k, v); });
    return request(`/jobs/nearby/?${params}`);
  },
  clickJob: (jobId) =>
    request(`/jobs/${jobId}/click/`, { method: "POST" }),
  companies: () => request(`/jobs/companies/`),
};

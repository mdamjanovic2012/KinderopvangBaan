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
  jobMapPins: (jobType) => {
    const qs = jobType ? `?job_type=${jobType}` : "";
    return request(`/jobs/map-pins/${qs}`);
  },
  jobs: (params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return request(`/jobs/?${qs}`);
  },
  job: (id) => request(`/jobs/${id}/`),
  nearbyJobs: ({ lat, lng, radius = 15, type } = {}) => {
    const params = new URLSearchParams({ lat, lng, radius });
    if (type) params.set("job_type", type);
    return request(`/jobs/nearby/?${params}`);
  },
  clickJob: (jobId) =>
    request(`/jobs/${jobId}/click/`, { method: "POST" }),
  companies: () => request(`/jobs/companies/`),
};

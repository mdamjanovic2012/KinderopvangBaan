const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

async function request(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  });
  if (!res.ok) throw await res.json();
  return res.json();
}

export const api = {
  // Institutions
  institutions: (params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return request(`/institutions/?${qs}`);
  },
  institution: (id) => request(`/institutions/${id}/`),
  nearbyInstitutions: ({ lat, lng, radius = 10, type } = {}) => {
    const params = new URLSearchParams({ lat, lng, radius });
    if (type) params.set("type", type);
    return request(`/institutions/nearby/?${params}`);
  },
  reviews: (id) => request(`/institutions/${id}/reviews/`),

  // Jobs
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
};

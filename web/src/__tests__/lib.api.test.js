/**
 * Tests for src/lib/api.js
 */
import { api } from "@/lib/api";

describe("API configuratie", () => {
  it("NEXT_PUBLIC_API_URL wijst niet naar localhost in productie", () => {
    const url = process.env.NEXT_PUBLIC_API_URL;
    // Als de variabele gezet is, mag het geen localhost zijn
    if (url) {
      expect(url).not.toMatch(/localhost|127\.0\.0\.1/);
      expect(url).toMatch(/^https:\/\//);
    }
  });

  it("API-aanroepen bevatten nooit een localhost-URL", async () => {
    const mockFetchLocal = (data) =>
      global.fetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => data,
      });
    mockFetchLocal({ results: [] });
    await api.jobs();
    const url = fetch.mock.calls[0][0];
    if (process.env.NEXT_PUBLIC_API_URL) {
      expect(url).not.toContain("localhost");
    }
  });
});

const mockFetch = (data, ok = true, status = 200) => {
  global.fetch.mockResolvedValueOnce({
    ok,
    status,
    json: async () => data,
  });
};

describe("api.institutions", () => {
  it("fetches all institutions without params", async () => {
    mockFetch({ results: [{ id: 1, name: "Test BSO" }] });
    const data = await api.institutions();
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/institutions/"),
      expect.any(Object)
    );
    expect(data.results[0].name).toBe("Test BSO");
  });

  it("passes query params correctly", async () => {
    mockFetch({ results: [] });
    await api.institutions({ institution_type: "bso", page_size: 10 });
    const url = fetch.mock.calls[0][0];
    expect(url).toContain("institution_type=bso");
    expect(url).toContain("page_size=10");
  });

  it("throws when response is not ok", async () => {
    mockFetch({ detail: "Not found" }, false, 404);
    await expect(api.institutions()).rejects.toEqual({ detail: "Not found" });
  });
});

describe("api.institution", () => {
  it("fetches single institution by id", async () => {
    mockFetch({ id: 5, name: "BSO De Kikker" });
    const data = await api.institution(5);
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/institutions/5/"),
      expect.any(Object)
    );
    expect(data.id).toBe(5);
  });
});

describe("api.nearbyInstitutions", () => {
  it("builds nearby URL with lat/lng/radius", async () => {
    mockFetch([]);
    await api.nearbyInstitutions({ lat: 52.37, lng: 4.89, radius: 10 });
    const url = fetch.mock.calls[0][0];
    expect(url).toContain("lat=52.37");
    expect(url).toContain("lng=4.89");
    expect(url).toContain("radius=10");
  });

  it("includes type param when provided", async () => {
    mockFetch([]);
    await api.nearbyInstitutions({ lat: 52.37, lng: 4.89, type: "bso" });
    const url = fetch.mock.calls[0][0];
    expect(url).toContain("type=bso");
  });

  it("defaults radius to 10", async () => {
    mockFetch([]);
    await api.nearbyInstitutions({ lat: 52.37, lng: 4.89 });
    const url = fetch.mock.calls[0][0];
    expect(url).toContain("radius=10");
  });
});

describe("api.reviews", () => {
  it("fetches reviews for institution", async () => {
    mockFetch([{ id: 1, rating: 4 }]);
    await api.reviews(3);
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/institutions/3/reviews/"),
      expect.any(Object)
    );
  });
});

describe("api.jobs", () => {
  it("fetches jobs without params", async () => {
    mockFetch({ results: [] });
    await api.jobs();
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/jobs/"),
      expect.any(Object)
    );
  });

  it("passes job_type filter", async () => {
    mockFetch({ results: [] });
    await api.jobs({ job_type: "kdv" });
    expect(fetch.mock.calls[0][0]).toContain("job_type=kdv");
  });
});

describe("api.job", () => {
  it("fetches single job", async () => {
    mockFetch({ id: 7, title: "Test job" });
    const data = await api.job(7);
    expect(data.title).toBe("Test job");
  });
});

describe("api.nearbyJobs", () => {
  it("builds URL with lat/lng/radius", async () => {
    mockFetch([]);
    await api.nearbyJobs({ lat: 51.92, lng: 4.48, radius: 15 });
    const url = fetch.mock.calls[0][0];
    expect(url).toContain("lat=51.92");
    expect(url).toContain("radius=15");
  });

  it("converts type to job_type param", async () => {
    mockFetch([]);
    await api.nearbyJobs({ lat: 51.92, lng: 4.48, type: "bso" });
    const url = fetch.mock.calls[0][0];
    expect(url).toContain("job_type=bso");
  });
});

describe("api.clickJob", () => {
  it("posts to click endpoint", async () => {
    mockFetch({ source_url: "https://kinderdam.nl/vacature/1" });
    await api.clickJob(5);
    const [url, opts] = fetch.mock.calls[0];
    expect(url).toContain("/jobs/5/click/");
    expect(opts.method).toBe("POST");
  });

  it("returns source_url", async () => {
    mockFetch({ source_url: "https://kinderdam.nl/vacature/1" });
    const data = await api.clickJob(5);
    expect(data.source_url).toBe("https://kinderdam.nl/vacature/1");
  });

  it("attaches bearer token when in localStorage", async () => {
    localStorage.setItem("kb_access", "test_token_xyz");
    mockFetch({ source_url: "https://example.com" });
    await api.clickJob(5);
    const [, opts] = fetch.mock.calls[0];
    expect(opts.headers.Authorization).toBe("Bearer test_token_xyz");
  });
});

describe("api.companies", () => {
  it("fetches companies list", async () => {
    mockFetch([{ id: 1, name: "Kinderdam" }]);
    await api.companies();
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/jobs/companies/"),
      expect.any(Object)
    );
  });
});

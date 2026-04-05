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

describe("api.jobMapPins", () => {
  it("fetches job map pins without filter", async () => {
    mockFetch({ total: 10, blurred: false, results: [] });
    const data = await api.jobMapPins();
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/jobs/map-pins/"),
      expect.any(Object)
    );
    expect(data.total).toBe(10);
  });

  it("includes job_type param when provided", async () => {
    mockFetch({ total: 5, blurred: false, results: [] });
    await api.jobMapPins({ job_type: "pm3" });
    const url = fetch.mock.calls[0][0];
    expect(url).toContain("job_type=pm3");
  });

  it("throws when response is not ok", async () => {
    mockFetch({ detail: "Server error" }, false, 500);
    await expect(api.jobMapPins()).rejects.toEqual({ detail: "Server error" });
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

  it("passes job_type param", async () => {
    mockFetch([]);
    await api.nearbyJobs({ lat: 51.92, lng: 4.48, job_type: "bso" });
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

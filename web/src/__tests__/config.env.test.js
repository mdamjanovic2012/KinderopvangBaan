/**
 * Productie-omgevingsvariabelen validatie
 *
 * Deze tests draaien in de CI/CD-pipeline met NEXT_PUBLIC_API_URL
 * ingesteld op de productie-URL. Ze falen als de variabelen ontbreken
 * of verkeerd geconfigureerd zijn vóór de deploymentbuild.
 *
 * Lokaal: tests worden overgeslagen als de variabele niet gezet is.
 * In de pipeline: NEXT_PUBLIC_API_URL is verplicht (zie web-deploy.yml).
 */

const PRODUCTION_API_URL = process.env.NEXT_PUBLIC_API_URL;
const IS_CI = process.env.CI === "true";

describe("Omgevingsvariabelen — productieconfiguratie", () => {
  it("NEXT_PUBLIC_API_URL is ingesteld in de CI-pipeline", () => {
    if (!IS_CI) return; // lokaal overslaan
    expect(PRODUCTION_API_URL).toBeDefined();
    expect(PRODUCTION_API_URL).not.toBe("");
  });

  it("NEXT_PUBLIC_API_URL gebruikt HTTPS (geen HTTP)", () => {
    if (!PRODUCTION_API_URL) return;
    expect(PRODUCTION_API_URL).toMatch(/^https:\/\//);
  });

  it("NEXT_PUBLIC_API_URL wijst niet naar localhost of 127.0.0.1", () => {
    if (!PRODUCTION_API_URL) return;
    expect(PRODUCTION_API_URL).not.toMatch(/localhost|127\.0\.0\.1/);
  });

  it("NEXT_PUBLIC_API_URL eindigt op /api", () => {
    if (!PRODUCTION_API_URL) return;
    expect(PRODUCTION_API_URL).toMatch(/\/api\/?$/);
  });

  it("NEXT_PUBLIC_API_URL verwijst naar de correcte Azure App Service", () => {
    if (!IS_CI) return; // enkel in CI strict controleren
    expect(PRODUCTION_API_URL).toContain("kinderopvangbaan-api");
  });
});

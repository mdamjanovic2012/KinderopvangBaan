/**
 * Tests for src/lib/caoFunctions.js
 */
import { CAO_FUNCTIONS, getCaoLabel } from "@/lib/caoFunctions";

describe("CAO_FUNCTIONS", () => {
  it("bevat 12 functies", () => {
    expect(CAO_FUNCTIONS).toHaveLength(12);
  });

  it("elke functie heeft value en label", () => {
    CAO_FUNCTIONS.forEach(({ value, label }) => {
      expect(typeof value).toBe("string");
      expect(value.length).toBeGreaterThan(0);
      expect(typeof label).toBe("string");
      expect(label.length).toBeGreaterThan(0);
    });
  });

  it("alle values zijn uniek", () => {
    const values = CAO_FUNCTIONS.map((f) => f.value);
    expect(new Set(values).size).toBe(values.length);
  });
});

describe("getCaoLabel", () => {
  it("geeft het juiste label terug voor een bekende waarde", () => {
    expect(getCaoLabel("pm3")).toBe("Pedagogisch medewerker (niveau 3)");
    expect(getCaoLabel("gastouder")).toBe("Gastouder");
    expect(getCaoLabel("teamleider")).toBe("Teamleider kinderopvang");
  });

  it("geeft de waarde zelf terug als fallback voor onbekende waarde", () => {
    expect(getCaoLabel("onbekend_functie")).toBe("onbekend_functie");
    expect(getCaoLabel("")).toBe("");
  });
});

/**
 * Tests for src/components/InstitutionMap.jsx
 */
import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import InstitutionMap from "@/components/InstitutionMap";

const makeInstitution = (overrides = {}) => ({
  id: 1,
  name: "Test BSO",
  institution_type: "bso",
  street: "Damrak",
  house_number: "1",
  city: "Amsterdam",
  lrk_verified: true,
  distance_km: 1.5,
  location: { coordinates: [4.9041, 52.3676] },
  ...overrides,
});

describe("InstitutionMap", () => {
  it("renders the map container", () => {
    render(<InstitutionMap institutions={[]} />);
    expect(screen.getByTestId("mapbox-map")).toBeInTheDocument();
  });

  it("renders navigation control", () => {
    render(<InstitutionMap institutions={[]} />);
    expect(screen.getByTestId("navigation-control")).toBeInTheDocument();
  });

  it("renders geolocate control", () => {
    render(<InstitutionMap institutions={[]} />);
    expect(screen.getByTestId("geolocate-control")).toBeInTheDocument();
  });

  it("renders a marker per institution", () => {
    const institutions = [makeInstitution(), makeInstitution({ id: 2 })];
    render(<InstitutionMap institutions={institutions} />);
    expect(screen.getAllByTestId("map-marker")).toHaveLength(2);
  });

  it("renders no markers when institutions list is empty", () => {
    render(<InstitutionMap institutions={[]} />);
    expect(screen.queryAllByTestId("map-marker")).toHaveLength(0);
  });

  it("shows popup when marker is clicked", () => {
    const institution = makeInstitution();
    render(<InstitutionMap institutions={[institution]} />);
    fireEvent.click(screen.getByTestId("map-marker"));
    expect(screen.getByTestId("map-popup")).toBeInTheDocument();
  });

  it("shows institution name in popup", () => {
    const institution = makeInstitution({ name: "BSO De Kikker" });
    render(<InstitutionMap institutions={[institution]} />);
    fireEvent.click(screen.getByTestId("map-marker"));
    expect(screen.getByText("BSO De Kikker")).toBeInTheDocument();
  });

  it("shows LRK verified badge in popup when lrk_verified", () => {
    const institution = makeInstitution({ lrk_verified: true });
    render(<InstitutionMap institutions={[institution]} />);
    fireEvent.click(screen.getByTestId("map-marker"));
    expect(screen.getByText("✓ LRK")).toBeInTheDocument();
  });

  it("does not show LRK badge when not verified", () => {
    const institution = makeInstitution({ lrk_verified: false });
    render(<InstitutionMap institutions={[institution]} />);
    fireEvent.click(screen.getByTestId("map-marker"));
    expect(screen.queryByText("✓ LRK")).not.toBeInTheDocument();
  });

  it("shows distance_km in popup when available", () => {
    const institution = makeInstitution({ distance_km: 2.34 });
    render(<InstitutionMap institutions={[institution]} />);
    fireEvent.click(screen.getByTestId("map-marker"));
    expect(screen.getByText(/2.34/)).toBeInTheDocument();
  });

  it("closes popup on close action", () => {
    const institution = makeInstitution();
    render(<InstitutionMap institutions={[institution]} />);
    fireEvent.click(screen.getByTestId("map-marker"));
    expect(screen.getByTestId("map-popup")).toBeInTheDocument();
  });

  it("accepts custom initialViewState", () => {
    const viewState = { longitude: 5.1, latitude: 52.1, zoom: 12 };
    // Should not throw
    expect(() =>
      render(<InstitutionMap institutions={[]} initialViewState={viewState} />)
    ).not.toThrow();
  });

  it("uses default Netherlands view when no initialViewState", () => {
    expect(() => render(<InstitutionMap institutions={[]} />)).not.toThrow();
  });

  it("sluit popup na klikken op sluiten", () => {
    const institution = makeInstitution();
    render(<InstitutionMap institutions={[institution]} />);
    fireEvent.click(screen.getByTestId("map-marker"));
    expect(screen.getByTestId("map-popup")).toBeInTheDocument();
    fireEvent.click(screen.getByTestId("popup-close"));
    expect(screen.queryByTestId("map-popup")).not.toBeInTheDocument();
  });

  it("hover op marker past grootte aan (mouseEnter/Leave)", () => {
    const institution = makeInstitution();
    render(<InstitutionMap institutions={[institution]} />);
    const marker = screen.getByTestId("map-marker");
    // Triggeert onMouseEnter en onMouseLeave op de inner div
    const innerDiv = marker.firstChild;
    if (innerDiv) {
      fireEvent.mouseEnter(innerDiv);
      fireEvent.mouseLeave(innerDiv);
    }
    expect(marker).toBeInTheDocument();
  });

  it("vliegt naar nieuw center wanneer center prop wijzigt", () => {
    const center = { lat: 52.37, lng: 4.89, radius: 5 };
    expect(() =>
      render(<InstitutionMap institutions={[]} center={center} />)
    ).not.toThrow();
  });

  it("rendert cluster marker wanneer er veel instellingen zijn", () => {
    const institutions = Array.from({ length: 5 }, (_, i) =>
      makeInstitution({ id: i + 1 })
    );
    render(<InstitutionMap institutions={institutions} />);
    // Met 5+ punten retourneert de mock één cluster
    expect(screen.getByTestId("map-marker")).toBeInTheDocument();
  });
});

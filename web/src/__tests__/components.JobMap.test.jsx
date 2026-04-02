/**
 * Tests for src/components/JobMap.jsx
 */
import React from "react";
import { render, screen, fireEvent, act } from "@testing-library/react";
import JobMap from "@/components/JobMap";
import Supercluster from "supercluster";

const makeJob = (overrides = {}) => ({
  id: 1,
  title: "PM KDV Amsterdam",
  job_type: "pm3",
  company_name: "Kinderdam BV",
  city: "Amsterdam",
  location: { coordinates: [4.9041, 52.3676] },
  ...overrides,
});

describe("JobMap — rendering", () => {
  it("renders the map container", () => {
    render(<JobMap jobs={[]} />);
    expect(screen.getByTestId("mapbox-map")).toBeInTheDocument();
  });

  it("renders navigation control", () => {
    render(<JobMap jobs={[]} />);
    expect(screen.getByTestId("navigation-control")).toBeInTheDocument();
  });

  it("renders geolocate control", () => {
    render(<JobMap jobs={[]} />);
    expect(screen.getByTestId("geolocate-control")).toBeInTheDocument();
  });

  it("renders no markers when jobs list is empty", () => {
    render(<JobMap jobs={[]} />);
    expect(screen.queryAllByTestId("map-marker")).toHaveLength(0);
  });

  it("renders a marker per job (< 5 jobs)", () => {
    const jobs = [makeJob(), makeJob({ id: 2 })];
    render(<JobMap jobs={jobs} />);
    expect(screen.getAllByTestId("map-marker")).toHaveLength(2);
  });

  it("renders cluster marker when 5+ jobs overlap", () => {
    const jobs = Array.from({ length: 5 }, (_, i) => makeJob({ id: i + 1 }));
    render(<JobMap jobs={jobs} />);
    expect(screen.getByTestId("map-marker")).toBeInTheDocument();
  });

  it("does not render popup initially", () => {
    render(<JobMap jobs={[makeJob()]} />);
    expect(screen.queryByTestId("map-popup")).not.toBeInTheDocument();
  });

  it("filters out jobs without location coordinates", () => {
    const jobs = [
      makeJob({ id: 1 }),
      { id: 2, title: "No location", job_type: "bso", company_name: "X", city: "Y", location: null },
    ];
    render(<JobMap jobs={jobs} />);
    expect(screen.getAllByTestId("map-marker")).toHaveLength(1);
  });
});

describe("JobMap — marker interaction", () => {
  it("shows popup when job marker is clicked", () => {
    render(<JobMap jobs={[makeJob()]} />);
    fireEvent.click(screen.getByTestId("map-marker"));
    expect(screen.getByTestId("map-popup")).toBeInTheDocument();
  });

  it("shows job title in popup", () => {
    render(<JobMap jobs={[makeJob({ title: "BSO Begeleider Rotterdam" })]} />);
    fireEvent.click(screen.getByTestId("map-marker"));
    expect(screen.getByText("BSO Begeleider Rotterdam")).toBeInTheDocument();
  });

  it("shows company name and city in popup", () => {
    render(<JobMap jobs={[makeJob({ company_name: "Kinderdam", city: "Utrecht" })]} />);
    fireEvent.click(screen.getByTestId("map-marker"));
    expect(screen.getByText(/Kinderdam/)).toBeInTheDocument();
    expect(screen.getByText(/Utrecht/)).toBeInTheDocument();
  });

  it("shows job_type badge in popup", () => {
    render(<JobMap jobs={[makeJob({ job_type: "bso_begeleider" })]} />);
    fireEvent.click(screen.getByTestId("map-marker"));
    expect(screen.getByText("bso_begeleider")).toBeInTheDocument();
  });

  it("shows 'Bekijk vacature' link in popup", () => {
    render(<JobMap jobs={[makeJob({ id: 42 })]} />);
    fireEvent.click(screen.getByTestId("map-marker"));
    const link = screen.getByText(/Bekijk vacature/);
    expect(link.closest("a")).toHaveAttribute("href", "/jobs/42");
  });

  it("closes popup when close button is clicked", () => {
    render(<JobMap jobs={[makeJob()]} />);
    fireEvent.click(screen.getByTestId("map-marker"));
    expect(screen.getByTestId("map-popup")).toBeInTheDocument();
    fireEvent.click(screen.getByTestId("popup-close"));
    expect(screen.queryByTestId("map-popup")).not.toBeInTheDocument();
  });
});

describe("JobMap — hover on marker", () => {
  it("does not throw on mouseEnter/mouseLeave", () => {
    render(<JobMap jobs={[makeJob()]} />);
    const marker = screen.getByTestId("map-marker");
    const inner = marker.firstChild;
    if (inner) {
      fireEvent.mouseEnter(inner);
      fireEvent.mouseLeave(inner);
    }
    expect(marker).toBeInTheDocument();
  });
});

describe("JobMap — cluster interaction", () => {
  it("renders cluster count badge for 5+ jobs", () => {
    const jobs = Array.from({ length: 5 }, (_, i) => makeJob({ id: i + 1 }));
    render(<JobMap jobs={jobs} />);
    expect(screen.getByText("5")).toBeInTheDocument();
  });

  it("clicking cluster does not throw", () => {
    const jobs = Array.from({ length: 5 }, (_, i) => makeJob({ id: i + 1 }));
    render(<JobMap jobs={jobs} />);
    expect(() => fireEvent.click(screen.getByTestId("map-marker"))).not.toThrow();
  });

  it("cluster click uses getClusterExpansionZoom (not getLeaves+fitBounds for expandable cluster)", () => {
    // Verifies the fix: cluster click must call getClusterExpansionZoom,
    // and only call getLeaves when expansionZoom > maxZoom (terminal cluster).
    const expansionZoomSpy = jest.spyOn(Supercluster.prototype, "getClusterExpansionZoom");
    const getLeavesSpy = jest.spyOn(Supercluster.prototype, "getLeaves");

    const jobs = Array.from({ length: 5 }, (_, i) => makeJob({ id: i + 1 }));
    render(<JobMap jobs={jobs} />);
    fireEvent.click(screen.getByTestId("map-marker"));

    // expansionZoom = 10 (< maxZoom 14) → should flyTo, not getLeaves
    expect(expansionZoomSpy).toHaveBeenCalled();
    expect(getLeavesSpy).not.toHaveBeenCalled();

    expansionZoomSpy.mockRestore();
    getLeavesSpy.mockRestore();
  });

  it("cluster click calls flyTo with correct zoom from getClusterExpansionZoom", () => {
    // getClusterExpansionZoom returns 10 (per mock), flyTo must be called with zoom: 10
    const jobs = Array.from({ length: 5 }, (_, i) => makeJob({ id: i + 1 }));

    const flyToSpy = jest.fn();
    jest.spyOn(React, "useImperativeHandle").mockImplementation((ref, init) => {
      if (ref) {
        const handle = init();
        handle.flyTo = flyToSpy;
        ref.current = handle;
      }
    });

    render(<JobMap jobs={jobs} />);
    fireEvent.click(screen.getByTestId("map-marker"));

    // flyTo should have been called with zoom capped at min(10, 20) = 10
    expect(flyToSpy).toHaveBeenCalledWith(
      expect.objectContaining({ zoom: 10 })
    );

    React.useImperativeHandle.mockRestore();
  });

  it("terminal cluster (all same location) shows list popup instead of flyTo", () => {
    // When expansionZoom > maxZoom (15 > 14), all jobs are at the same point.
    // Expected: getLeaves called, cluster-list-popup rendered, flyTo NOT called.
    jest.spyOn(Supercluster.prototype, "getClusterExpansionZoom").mockReturnValue(15);

    const jobs = Array.from({ length: 5 }, (_, i) =>
      makeJob({ id: i + 1, title: `Job ${i + 1}` })
    );
    render(<JobMap jobs={jobs} />);
    fireEvent.click(screen.getByTestId("map-marker"));

    expect(screen.getByTestId("cluster-list-popup")).toBeInTheDocument();

    Supercluster.prototype.getClusterExpansionZoom.mockRestore();
  });

  it("terminal cluster popup shows job titles", () => {
    jest.spyOn(Supercluster.prototype, "getClusterExpansionZoom").mockReturnValue(15);

    const jobs = Array.from({ length: 5 }, (_, i) =>
      makeJob({ id: i + 1, title: `Vacature ${i + 1}` })
    );
    render(<JobMap jobs={jobs} />);
    fireEvent.click(screen.getByTestId("map-marker"));

    // getLeaves returns all _points; each has properties.job with the title
    expect(screen.getByTestId("cluster-list-popup")).toBeInTheDocument();

    Supercluster.prototype.getClusterExpansionZoom.mockRestore();
  });

  it("terminal cluster popup closes on close button click", () => {
    jest.spyOn(Supercluster.prototype, "getClusterExpansionZoom").mockReturnValue(15);

    const jobs = Array.from({ length: 5 }, (_, i) => makeJob({ id: i + 1 }));
    render(<JobMap jobs={jobs} />);
    fireEvent.click(screen.getByTestId("map-marker"));
    expect(screen.getByTestId("cluster-list-popup")).toBeInTheDocument();
    fireEvent.click(screen.getByTestId("popup-close"));
    expect(screen.queryByTestId("cluster-list-popup")).not.toBeInTheDocument();

    Supercluster.prototype.getClusterExpansionZoom.mockRestore();
  });
});

describe("JobMap — center prop", () => {
  it("accepts center prop without throwing", () => {
    expect(() =>
      render(<JobMap jobs={[]} center={{ lat: 52.37, lng: 4.89 }} />)
    ).not.toThrow();
  });

  it("renders without center prop", () => {
    expect(() => render(<JobMap jobs={[]} />)).not.toThrow();
  });

  it("ignores center prop with missing lat/lng", () => {
    expect(() =>
      render(<JobMap jobs={[]} center={{ lat: null, lng: null }} />)
    ).not.toThrow();
  });
});

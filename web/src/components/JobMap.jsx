"use client";

import { useState, useCallback, useRef, useMemo, useEffect } from "react";
import Map, { Marker, Popup, NavigationControl, GeolocateControl } from "react-map-gl/maplibre";
import Supercluster from "supercluster";
import "maplibre-gl/dist/maplibre-gl.css";

function ClusterMarker({ count, lng, lat, onClick }) {
  const size = Math.min(16 + Math.sqrt(count) * 3, 52);
  return (
    <Marker longitude={lng} latitude={lat} anchor="center" onClick={onClick}>
      <div
        style={{
          width: size, height: size, borderRadius: "50%",
          backgroundColor: "#1d4ed8", border: "2.5px solid white",
          boxShadow: "0 2px 8px rgba(0,0,0,0.25)", display: "flex",
          alignItems: "center", justifyContent: "center",
          color: "white", fontSize: Math.max(10, size * 0.35),
          fontWeight: "700", cursor: "pointer",
        }}
      >
        {count}
      </div>
    </Marker>
  );
}

function JobMarker({ job, onClick }) {
  const [hovered, setHovered] = useState(false);
  const [lng, lat] = job.location.coordinates;

  return (
    <Marker longitude={lng} latitude={lat} anchor="bottom" onClick={() => onClick(job)}>
      <div
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
        style={{
          width: hovered ? 18 : 14, height: hovered ? 18 : 14,
          borderRadius: "50%", backgroundColor: "#1d4ed8",
          border: "2.5px solid white",
          boxShadow: "0 2px 6px rgba(0,0,0,0.25)",
          cursor: "pointer", transition: "all 0.15s ease",
        }}
      />
    </Marker>
  );
}

function JobPopup({ job, onClose }) {
  if (!job) return null;
  const [lng, lat] = job.location.coordinates;

  return (
    <Popup longitude={lng} latitude={lat} anchor="top" onClose={onClose}
      closeButton={true} closeOnClick={false} maxWidth="280px">
      <div className="p-2">
        <span className="text-xs font-semibold px-2 py-0.5 rounded-full text-white bg-blue-700 mb-1 inline-block">
          {job.job_type}
        </span>
        <h3 className="font-semibold text-gray-900 text-sm leading-tight mb-0.5">
          {job.title}
        </h3>
        <p className="text-xs text-gray-500 mb-2">{job.company_name} · {job.city}</p>
        <a
          href={`/jobs/${job.id}`}
          className="block text-center text-xs font-semibold text-white bg-blue-700 hover:bg-blue-800 rounded-lg py-1.5 transition-colors"
        >
          Bekijk vacature →
        </a>
      </div>
    </Popup>
  );
}

export default function JobMap({ jobs = [], center }) {
  const [selectedJob, setSelectedJob] = useState(null);
  const [viewState, setViewState] = useState({ longitude: 5.2913, latitude: 52.1326, zoom: 7 });
  const mapRef = useRef(null);

  useEffect(() => {
    if (center?.lat && center?.lng) {
      setViewState((v) => ({ ...v, longitude: center.lng, latitude: center.lat, zoom: 10 }));
    }
  }, [center]);

  const handleMarkerClick = useCallback((job) => setSelectedJob(job), []);

  const supercluster = useMemo(() => {
    const sc = new Supercluster({ radius: 50, maxZoom: 14 });
    sc.load(
      jobs
        .filter((j) => j.location?.coordinates)
        .map((j) => ({
          type: "Feature",
          geometry: { type: "Point", coordinates: j.location.coordinates },
          properties: { job: j },
        }))
    );
    return sc;
  }, [jobs]);

  const clusters = useMemo(() => {
    const zoom = Math.floor(viewState.zoom);
    try {
      return supercluster.getClusters([-180, -85, 180, 85], zoom);
    } catch {
      return [];
    }
  }, [supercluster, viewState.zoom]);

  return (
    <Map
      ref={mapRef}
      {...viewState}
      onMove={(e) => setViewState(e.viewState)}
      style={{ width: "100%", height: "100%" }}
      mapStyle="https://tiles.openfreemap.org/styles/liberty"
    >
      <NavigationControl position="top-right" />
      <GeolocateControl position="top-right" trackUserLocation showUserHeading />

      {clusters.map((feature) => {
        const [lng, lat] = feature.geometry.coordinates;
        if (feature.properties.cluster) {
          return (
            <ClusterMarker
              key={`cluster-${feature.id}`}
              count={feature.properties.point_count}
              lng={lng} lat={lat}
              onClick={() => {
                const expansionZoom = Math.min(
                  supercluster.getClusterExpansionZoom(feature.id),
                  20
                );
                mapRef.current?.flyTo?.({
                  center: [lng, lat],
                  zoom: expansionZoom,
                  duration: 500,
                });
              }}
            />
          );
        }
        const job = feature.properties.job;
        return <JobMarker key={job.id} job={job} onClick={handleMarkerClick} />;
      })}

      {selectedJob && <JobPopup job={selectedJob} onClose={() => setSelectedJob(null)} />}
    </Map>
  );
}

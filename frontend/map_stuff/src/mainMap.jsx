import React, { useEffect, useMemo, useState } from "react";
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  Circle,
  useMapEvents,
  useMap,
} from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { apiClient, normalizeApiError } from '@shared/api/client';

// Reliable CDN Icon Assets
const DefaultIcon = L.icon({
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
});

const jobIcon = L.icon({
  iconUrl: "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-red.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
});

const matchIcon = L.icon({
  iconUrl: "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-green.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
});

const emptyIcon = L.icon({
  iconUrl: "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-grey.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
});

const DEFAULT_CENTER = [27.7172, 85.324];
const DEFAULT_RADIUS_METERS = 5000;

function toFiniteNumber(value) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function extractLatLng(candidate) {
  if (!candidate) {
    return null;
  }

  if (Array.isArray(candidate) && candidate.length >= 2) {
    const latitude = toFiniteNumber(candidate[0]);
    const longitude = toFiniteNumber(candidate[1]);
    return latitude !== null && longitude !== null ? [latitude, longitude] : null;
  }

  if (typeof candidate !== "object") {
    return null;
  }

  const latitude = toFiniteNumber(
    candidate.latitude ?? candidate.lat ?? candidate.y ?? candidate[0]
  );
  const longitude = toFiniteNumber(
    candidate.longitude ?? candidate.lng ?? candidate.lon ?? candidate.x ?? candidate[1]
  );

  if (latitude !== null && longitude !== null) {
    return [latitude, longitude];
  }

  return extractLatLng(
    candidate.coordinates ?? candidate.coord ?? candidate.location ?? candidate.point ?? candidate.geometry
  );
}

function asTagList(value) {
  if (!value) {
    return [];
  }

  if (Array.isArray(value)) {
    return value.filter(Boolean).map(String);
  }

  if (typeof value === "string") {
    return value
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);
  }

  return [String(value)];
}

function formatRadius(value) {
  const radius = toFiniteNumber(value);
  if (radius === null) {
    return "n/a";
  }

  return radius >= 1000 ? `${(radius / 1000).toFixed(1)} km` : `${radius} m`;
}

function normalizeMatch(match, index) {
  const resolvedPosition =
    extractLatLng(match?.location) ??
    extractLatLng(match?.coords) ??
    extractLatLng(match?.coordinates) ??
    extractLatLng(match?.point) ??
    extractLatLng(match?.geometry) ??
    extractLatLng(match?.worker?.location) ??
    extractLatLng(match?.worker?.coords) ??
    extractLatLng(match?.worker?.coordinates) ??
    extractLatLng(match?.job_location) ??
    extractLatLng(match?.search_location) ??
    null;

  const workerTags =
    asTagList(match?.worker_tags) ||
    asTagList(match?.tags) ||
    asTagList(match?.worker?.tags) ||
    asTagList(match?.skill_tags) ||
    asTagList(match?.skills);

  const radius =
    toFiniteNumber(match?.radius) ??
    toFiniteNumber(match?.match_radius) ??
    toFiniteNumber(match?.distance_radius) ??
    toFiniteNumber(match?.search_radius) ??
    null;

  const distance =
    toFiniteNumber(match?.distance) ??
    toFiniteNumber(match?.distance_meters) ??
    toFiniteNumber(match?.distanceMeters) ??
    null;

  return {
    key:
      String(
        match?.worker_id ??
          match?.worker?.id ??
          match?.user_id ??
          match?.id ??
          match?.name ??
          index
      ),
    label:
      match?.worker_name ??
      match?.worker?.name ??
      match?.username ??
      match?.name ??
      `Match #${index + 1}`,
    workerId:
      match?.worker_id ??
      match?.worker?.id ??
      match?.user_id ??
      match?.id ??
      null,
    position: resolvedPosition,
    workerTags,
    radius,
    distance,
    status: match?.status ?? match?.match_status ?? "matched",
    raw: match,
  };
}

// SUB-COMPONENT: Listens for map clicks and fires the API payload
function MapClickHandler({ onMapClick }) {
  useMapEvents({
    click: (e) => {
      onMapClick([e.latlng.lat, e.latlng.lng]);
    },
  });
  return null;
}

function MapViewportController({ focusPoints }) {
  const map = useMap();

  useEffect(() => {
    if (!focusPoints.length) {
      map.setView(DEFAULT_CENTER, 13, { animate: true });
      return;
    }

    if (focusPoints.length === 1) {
      map.setView(focusPoints[0], 14, { animate: true });
      return;
    }

    map.fitBounds(L.latLngBounds(focusPoints), {
      padding: [48, 48],
      maxZoom: 15,
      animate: true,
    });
  }, [focusPoints, map]);

  return null;
}

function MainMap() {
  const [queryPoint, setQueryPoint] = useState(DEFAULT_CENTER); // Kathmandu center
  const [radius] = useState(DEFAULT_RADIUS_METERS); // UI visual helper (meters)
  const [jobTag, setJobTag] = useState("plumber");

  const [loading, setLoading] = useState(false);
  const [matches, setMatches] = useState([]);
  const [responseMeta, setResponseMeta] = useState({
    status: "idle",
    totalMatches: 0,
  });
  const [feedback, setFeedback] = useState({
    kind: "idle",
    message: "Click the map to query the PostGIS match engine.",
  });

  const visiblePoints = useMemo(() => {
    const points = [queryPoint];

    matches.forEach((match) => {
      if (match.position) {
        points.push(match.position);
      }
    });

    return points;
  }, [matches, queryPoint]);

  // THE LIVE NETWORK CONNECTION PIPELINE
  const handleMapClick = async (coords) => {
    setLoading(true);
    setQueryPoint(coords); // Store location instantly to drop the pin
    setMatches([]);
    setResponseMeta({ status: "loading", totalMatches: 0 });
    setFeedback({
      kind: "loading",
      message: "Querying PostGIS for live matches...",
    });

    try {
      const result = await apiClient.post('/api/jobs/match', {
        title: "Live Map Job Request",
        tag: jobTag,
        latitude: coords[0], // Lat
        longitude: coords[1], // Long
      });

      const normalizedMatches = Array.isArray(result?.matches)
        ? result.matches.map(normalizeMatch)
        : [];
      const totalMatches = toFiniteNumber(result?.total_matches) ?? normalizedMatches.length;

      setMatches(normalizedMatches);
      setResponseMeta({
        status: result?.status ?? (normalizedMatches.length ? "success" : "empty"),
        totalMatches,
      });

      if (!response.ok) {
        throw new Error(result?.detail || `Match request failed with status ${response.status}.`);
      }

      if (normalizedMatches.length > 0) {
        setFeedback({
          kind: "success",
          message: `Found ${totalMatches} live match${totalMatches === 1 ? "" : "es"} for ${jobTag}.`,
        });
      } else {
        setFeedback({
          kind: "empty",
          message: "The API returned no live matches for this request.",
        });
      }
    } catch (error) {
      console.error("Error matching job via backend:", error);
      setMatches([]);
      setResponseMeta({ status: "error", totalMatches: 0 });
      const normalized = normalizeApiError(error, "Unable to reach the match service. Please check your network or backend server.");
      setFeedback({
        kind: "error",
        message: normalized.message,
      });
    } finally {
      setLoading(false);
    }
  };

  const matchListPreview = matches.slice(0, 5);

  return (
    <div style={{ position: "relative", width: "100%", height: "100vh", background: "#e5ecf3" }}>
      
      {/* SIDE CONTROL PANEL */}
      <div
        style={{
          position: "absolute",
          top: "20px",
          right: "20px",
          zIndex: 1000,
          background: "rgba(255,255,255,0.96)",
          padding: "16px",
          borderRadius: "14px",
          boxShadow: "0 16px 36px rgba(15, 23, 42, 0.16)",
          fontFamily: "Inter, system-ui, sans-serif",
          width: "320px",
          backdropFilter: "blur(10px)",
          border: "1px solid rgba(148, 163, 184, 0.25)",
        }}
      >
        <h4 style={{ margin: "0 0 6px 0", fontSize: "16px" }}>Live PostGIS Sandbox</h4>
        <p style={{ fontSize: "12px", color: "#64748b", margin: "0 0 12px 0", lineHeight: 1.5 }}>
          Click anywhere on the map to query the worker index and render the live matches returned by the backend.
        </p>

        <label style={{ fontSize: "13px", fontWeight: "bold" }}>
          Job Category to Submit:
          <select
            value={jobTag}
            onChange={(e) => setJobTag(e.target.value)}
            style={{
              display: "block",
              width: "100%",
              marginTop: "5px",
              padding: "4px",
            }}
          >
            <option value="plumber">Plumber (Matches DB Worker)</option>
            <option value="electrician">Electrician (Mismatch)</option>
          </select>
        </label>

        <div style={{ marginTop: "12px", fontSize: "12px", color: "#475569", lineHeight: 1.5 }}>
          <div><strong>Search radius:</strong> {formatRadius(radius)}</div>
          <div><strong>Latest response:</strong> {responseMeta.status}</div>
          <div><strong>Live matches:</strong> {responseMeta.totalMatches}</div>
        </div>

        <hr style={{ margin: "15px 0" }} />

        {/* LIVE DATABASE FEEDBACK BOX */}
        <div
          style={{
            padding: "10px",
            borderRadius: "10px",
            backgroundColor:
              feedback.kind === "loading"
                ? "#fef7e0"
                : feedback.kind === "success"
                  ? "#e6f4ea"
                  : feedback.kind === "error"
                    ? "#fce8e6"
                    : feedback.kind === "empty"
                      ? "#f8fafc"
                      : "#f1f5f9",
            border: "1px solid rgba(148, 163, 184, 0.18)",
          }}
        >
          <b
            style={{
              display: "block",
              color:
                feedback.kind === "loading"
                  ? "#b06000"
                  : feedback.kind === "success"
                    ? "#137333"
                    : feedback.kind === "error"
                      ? "#c5221f"
                      : feedback.kind === "empty"
                        ? "#475569"
                        : "#5f6368",
            }}
          >
            {feedback.message}
          </b>
          <span style={{ fontSize: "11px", display: "block", marginTop: "5px", color: "#555" }}>
            Click: {queryPoint[0].toFixed(4)} | {queryPoint[1].toFixed(4)}
          </span>
          {matches.length > 0 && (
            <span style={{ fontSize: "11px", display: "block", marginTop: "4px", color: "#555" }}>
              Backend returned {matches.length} rendered match{matches.length === 1 ? "" : "es"}.
            </span>
          )}
        </div>

        <div style={{ marginTop: "12px" }}>
          <div style={{ fontSize: "12px", fontWeight: 700, marginBottom: "8px", color: "#0f172a" }}>
            Match preview
          </div>
          {matchListPreview.length > 0 ? (
            <div style={{ display: "grid", gap: "8px" }}>
              {matchListPreview.map((match) => (
                <div
                  key={match.key}
                  style={{
                    borderRadius: "10px",
                    border: "1px solid rgba(148, 163, 184, 0.22)",
                    background: "#fff",
                    padding: "8px 10px",
                    fontSize: "12px",
                    lineHeight: 1.45,
                  }}
                >
                  <div style={{ fontWeight: 700, color: "#0f172a" }}>{match.label}</div>
                  <div style={{ color: "#475569" }}>
                    Worker ID: {match.workerId ?? "n/a"}
                  </div>
                  <div style={{ color: "#475569" }}>
                    Radius: {formatRadius(match.radius)}
                  </div>
                  <div style={{ color: "#475569" }}>
                    Tags: {match.workerTags.length ? match.workerTags.join(", ") : "n/a"}
                  </div>
                  {match.distance !== null && (
                    <div style={{ color: "#475569" }}>
                      Distance: {formatRadius(match.distance)}
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div
              style={{
                fontSize: "12px",
                color: feedback.kind === "error" ? "#991b1b" : "#475569",
                borderRadius: "10px",
                border: "1px dashed rgba(148, 163, 184, 0.35)",
                padding: "10px",
                background: "rgba(248, 250, 252, 0.75)",
              }}
            >
              {loading
                ? "Waiting for backend response..."
                : feedback.kind === "empty"
                  ? "The backend returned an empty match set."
                  : feedback.kind === "error"
                    ? feedback.message
                    : "No matches rendered yet."}
            </div>
          )}
        </div>
      </div>

      {/* LEAFLET CANVAS MAP LAYER */}
      <MapContainer
        center={DEFAULT_CENTER}
        zoom={13}
        scrollWheelZoom={true}
        style={{ width: "100%", height: "100%" }}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        <MapClickHandler onMapClick={handleMapClick} />
        <MapViewportController focusPoints={visiblePoints} />

        {/* Search anchor pin */}
        <Marker position={queryPoint} icon={jobIcon}>
          <Popup>
            <b>Search Request</b>
            <br />
            Category: {jobTag}
            <br />
            Center: {queryPoint[0].toFixed(4)}, {queryPoint[1].toFixed(4)}
          </Popup>
        </Marker>

        {/* Search radius */}
        <Circle
          center={queryPoint}
          radius={radius}
          pathOptions={{
            color: "#1a73e8",
            fillColor: "#1a73e8",
            fillOpacity: 0.1,
          }}
        />

        {/* Live worker matches returned by PostGIS */}
        {matches.map((match) =>
          match.position ? (
            <Marker key={match.key} position={match.position} icon={matchIcon}>
              <Popup>
                <div style={{ fontFamily: "Inter, system-ui, sans-serif", lineHeight: 1.5 }}>
                  <strong>{match.label}</strong>
                  <br />
                  Worker ID: {match.workerId ?? "n/a"}
                  <br />
                  Radius: {formatRadius(match.radius)}
                  <br />
                  Tags: {match.workerTags.length ? match.workerTags.join(", ") : "n/a"}
                  <br />
                  {match.distance !== null ? (
                    <>
                      Distance: {formatRadius(match.distance)}
                      <br />
                    </>
                  ) : null}
                  <b style={{ color: "#137333" }}>Live PostGIS match</b>
                </div>
              </Popup>
            </Marker>
          ) : (
            <Marker key={`${match.key}-fallback`} position={queryPoint} icon={emptyIcon}>
              <Popup>
                <div style={{ fontFamily: "Inter, system-ui, sans-serif", lineHeight: 1.5 }}>
                  <strong>{match.label}</strong>
                  <br />
                  Worker ID: {match.workerId ?? "n/a"}
                  <br />
                  Radius: {formatRadius(match.radius)}
                  <br />
                  Tags: {match.workerTags.length ? match.workerTags.join(", ") : "n/a"}
                  <br />
                  <b style={{ color: "#b06000" }}>
                    Match data did not include coordinates, so the marker is anchored to the query point.
                  </b>
                </div>
              </Popup>
            </Marker>
          )
        )}
      </MapContainer>
    </div>
  );
}

export default MainMap;
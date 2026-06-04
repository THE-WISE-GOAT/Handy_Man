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

// Map Visual Asset Settings
const LEAFLET_CDN_ROOT = "https://unpkg.com/leaflet@1.9.4/dist/images";
const GITHUB_MARKER_ROOT = "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img";

const DefaultIcon = L.icon({
  iconUrl: `${LEAFLET_CDN_ROOT}/marker-icon.png`,
  shadowUrl: `${LEAFLET_CDN_ROOT}/marker-shadow.png`,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
});

const jobIcon = L.icon({
  iconUrl: `${GITHUB_MARKER_ROOT}/marker-icon-red.png`,
  shadowUrl: `${LEAFLET_CDN_ROOT}/marker-shadow.png`,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
});

const matchIcon = L.icon({
  iconUrl: `${GITHUB_MARKER_ROOT}/marker-icon-green.png`,
  shadowUrl: `${LEAFLET_CDN_ROOT}/marker-shadow.png`,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
});

const emptyIcon = L.icon({
  iconUrl: `${GITHUB_MARKER_ROOT}/marker-icon-grey.png`,
  shadowUrl: `${LEAFLET_CDN_ROOT}/marker-shadow.png`,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
});

const DEFAULT_CENTER = [27.7172, 85.324];
const DEFAULT_RADIUS_METERS = 5000;

function toFiniteNumber(value) {
  const num = Number(value);
  return Number.isFinite(num) ? num : null;
}

function extractLatLng(candidate) {
  if (!candidate) return null;

  if (Array.isArray(candidate) && candidate.length >= 2) {
    const lat = toFiniteNumber(candidate[0]);
    const lng = toFiniteNumber(candidate[1]);
    return (lat !== null && lng !== null) ? [lat, lng] : null;
  }

  if (typeof candidate !== "object") return null;

  const resolvedLat = toFiniteNumber(candidate.latitude ?? candidate.lat ?? candidate.y ?? candidate[0]);
  const resolvedLng = toFiniteNumber(candidate.longitude ?? candidate.lng ?? candidate.lon ?? candidate.x ?? candidate[1]);

  if (resolvedLat !== null && resolvedLng !== null) {
    return [resolvedLat, resolvedLng];
  }

  const fallbackProperty = candidate.coordinates ?? candidate.coord ?? candidate.location ?? candidate.point ?? candidate.geometry;
  return extractLatLng(fallbackProperty);
}

function asTagList(value) {
  if (!value) return [];
  if (Array.isArray(value)) return value.filter(Boolean).map(String);
  
  if (typeof value === "string") {
    return value.split(",").map(str => str.trim()).filter(Boolean);
  }
  return [String(value)];
}

function formatRadius(value) {
  const val = toFiniteNumber(value);
  if (val === null) return "n/a";
  return val >= 1000 ? `${(val / 1000).toFixed(1)} km` : `${val} m`;
}

function normalizeMatch(item, idx) {
  const resolvedPosition =
    extractLatLng(item?.location) ??
    extractLatLng(item?.coords) ??
    extractLatLng(item?.coordinates) ??
    extractLatLng(item?.point) ??
    extractLatLng(item?.geometry) ??
    extractLatLng(item?.worker?.location) ??
    extractLatLng(item?.worker?.coords) ??
    extractLatLng(item?.worker?.coordinates) ??
    extractLatLng(item?.job_location) ??
    extractLatLng(item?.search_location) ??
    null;

  const workerTags =
    asTagList(item?.worker_tags) ||
    asTagList(item?.tags) ||
    asTagList(item?.worker?.tags) ||
    asTagList(item?.skill_tags) ||
    asTagList(item?.skills);

  const radius =
    toFiniteNumber(item?.radius) ??
    toFiniteNumber(item?.match_radius) ??
    toFiniteNumber(item?.distance_radius) ??
    toFiniteNumber(item?.search_radius) ??
    null;

  const distance =
    toFiniteNumber(item?.distance) ??
    toFiniteNumber(item?.distance_meters) ??
    toFiniteNumber(item?.distanceMeters) ??
    null;

  return {
    key: String(item?.worker_id ?? item?.worker?.id ?? item?.user_id ?? item?.id ?? item?.name ?? idx),
    label: item?.worker_name ?? item?.worker?.name ?? item?.username ?? item?.name ?? `Match #${idx + 1}`,
    workerId: item?.worker_id ?? item?.worker?.id ?? item?.user_id ?? item?.id ?? null,
    position: resolvedPosition,
    workerTags,
    radius,
    distance,
    status: item?.status ?? item?.match_status ?? "matched",
    raw: item,
  };
}

function MapClickHandler({ onMapClick }) {
  useMapEvents({
    click: (event) => onMapClick([event.latlng.lat, event.latlng.lng]),
  });
  return null;
}

function MapViewportController({ focusPoints }) {
  const leafletMapInstance = useMap();

  useEffect(() => {
    if (!focusPoints.length) {
      leafletMapInstance.setView(DEFAULT_CENTER, 13, { animate: true });
      return;
    }

    if (focusPoints.length === 1) {
      leafletMapInstance.setView(focusPoints[0], 14, { animate: true });
      return;
    }

    leafletMapInstance.fitBounds(L.latLngBounds(focusPoints), {
      padding: [48, 48],
      maxZoom: 15,
      animate: true,
    });
  }, [focusPoints, leafletMapInstance]);

  return null;
}

// Visual layout configuration constants to reduce workspace clutter
const STYLES = {
  viewWrapper: { position: "relative", width: "100%", height: "100vh", background: "#e5ecf3" },
  controlPanel: {
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
  }
};

function MainMap() {
  const [queryPoint, setQueryPoint] = useState(DEFAULT_CENTER);
  const [radius] = useState(DEFAULT_RADIUS_METERS);
  const [jobTag, setJobTag] = useState("plumber");
  const [loading, setLoading] = useState(false);
  const [matches, setMatches] = useState([]);
  
  const [responseMeta, setResponseMeta] = useState({ status: "idle", totalMatches: 0 });
  const [feedback, setFeedback] = useState({ kind: "idle", message: "Click the map to query the PostGIS match engine." });

  const visiblePoints = useMemo(() => {
    const outputPoints = [queryPoint];
    matches.forEach((item) => {
      if (item.position) outputPoints.push(item.position);
    });
    return outputPoints;
  }, [matches, queryPoint]);

  const handleMapClick = async (coords) => {
    setLoading(true);
    setQueryPoint(coords);
    setMatches([]);
    setResponseMeta({ status: "loading", totalMatches: 0 });
    setFeedback({ kind: "loading", message: "Querying PostGIS for live matches..." });

    try {
      const serverPayload = await apiClient.post('/api/jobs/match', {
        title: "Live Map Job Request",
        tag: jobTag,
        latitude: coords[0],
        longitude: coords[1],
      });

      const processedRecords = Array.isArray(serverPayload?.matches)
        ? serverPayload.matches.map(normalizeMatch)
        : [];
      
      const aggregateCount = toFiniteNumber(serverPayload?.total_matches) ?? processedRecords.length;

      setMatches(processedRecords);
      setResponseMeta({
        status: serverPayload?.status ?? (processedRecords.length ? "success" : "empty"),
        totalMatches: aggregateCount,
      });

      if (!response.ok) {
        throw new Error(serverPayload?.detail || `Match request failed with status ${response.status}.`);
      }

      if (processedRecords.length > 0) {
        setFeedback({
          kind: "success",
          message: `Found ${aggregateCount} live match${aggregateCount === 1 ? "" : "es"} for ${jobTag}.`,
        });
      } else {
        setFeedback({
          kind: "empty",
          message: "The API returned no live matches for this request.",
        });
      }
    } catch (err) {
      console.error("Error matching job via backend:", err);
      setMatches([]);
      setResponseMeta({ status: "error", totalMatches: 0 });
      
      const parsedError = normalizeApiError(err, "Unable to reach the match service. Please check your network or backend server.");
      setFeedback({ kind: "error", message: parsedError.message });
    } finally {
      setLoading(false);
    }
  };

  const getStatusBgColor = (kind) => {
    switch (kind) {
      case "loading": return "#fef7e0";
      case "success": return "#e6f4ea";
      case "error":   return "#fce8e6";
      case "empty":   return "#f8fafc";
      default:        return "#f1f5f9";
    }
  };

  const getStatusTextColor = (kind) => {
    switch (kind) {
      case "loading": return "#b06000";
      case "success": return "#137333";
      case "error":   return "#c5221f";
      case "empty":   return "#475569";
      default:        return "#5f6368";
    }
  };

  return (
    <div style={STYLES.viewWrapper}>
      
      {/* SIDE CONTROL PANEL */}
      <div style={STYLES.controlPanel}>
        <h4 style={{ margin: "0 0 6px 0", fontSize: "16px" }}>Live PostGIS Sandbox</h4>
        <p style={{ fontSize: "12px", color: "#64748b", margin: "0 0 12px 0", lineHeight: 1.5 }}>
          Click anywhere on the map to query the worker index and render the live matches returned by the backend.
        </p>

        <label style={{ fontSize: "13px", fontWeight: "bold" }}>
          Job Category to Submit:
          <select
            value={jobTag}
            onChange={(e) => setJobTag(e.target.value)}
            style={{ display: "block", width: "100%", marginTop: "5px", padding: "4px" }}
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
            backgroundColor: getStatusBgColor(feedback.kind),
            border: "1px solid rgba(148, 163, 184, 0.18)",
          }}
        >
          <b style={{ display: "block", color: getStatusTextColor(feedback.kind) }}>
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
          {matches.length > 0 ? (
            <div style={{ display: "grid", gap: "8px" }}>
              {matches.slice(0, 5).map((item) => (
                <div
                  key={item.key}
                  style={{
                    borderRadius: "10px",
                    border: "1px solid rgba(148, 163, 184, 0.22)",
                    background: "#fff",
                    padding: "8px 10px",
                    fontSize: "12px",
                    lineHeight: 1.45,
                  }}
                >
                  <div style={{ fontWeight: 700, color: "#0f172a" }}>{item.label}</div>
                  <div style={{ color: "#475569" }}>Worker ID: {item.workerId ?? "n/a"}</div>
                  <div style={{ color: "#475569" }}>Radius: {formatRadius(item.radius)}</div>
                  <div style={{ color: "#475569" }}>
                    Tags: {item.workerTags.length ? item.workerTags.join(", ") : "n/a"}
                  </div>
                  {item.distance !== null && (
                    <div style={{ color: "#475569" }}>Distance: {formatRadius(item.distance)}</div>
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
        {matches.map((item) =>
          item.position ? (
            <Marker key={item.key} position={item.position} icon={matchIcon}>
              <Popup>
                <div style={{ fontFamily: "Inter, system-ui, sans-serif", lineHeight: 1.5 }}>
                  <strong>{item.label}</strong>
                  <br />
                  Worker ID: {item.workerId ?? "n/a"}
                  <br />
                  Radius: {formatRadius(item.radius)}
                  <br />
                  Tags: {item.workerTags.length ? item.workerTags.join(", ") : "n/a"}
                  <br />
                  {item.distance !== null && (
                    <>
                      Distance: {formatRadius(item.distance)}
                      <br />
                    </>
                  )}
                  <b style={{ color: "#137333" }}>Live PostGIS match</b>
                </div>
              </Popup>
            </Marker>
          ) : (
            <Marker key={`${item.key}-fallback`} position={queryPoint} icon={emptyIcon}>
              <Popup>
                <div style={{ fontFamily: "Inter, system-ui, sans-serif", lineHeight: 1.5 }}>
                  <strong>{item.label}</strong>
                  <br />
                  Worker ID: {item.workerId ?? "n/a"}
                  <br />
                  Radius: {formatRadius(item.radius)}
                  <br />
                  Tags: {item.workerTags.length ? item.workerTags.join(", ") : "n/a"}
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
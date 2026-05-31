import React, { useState } from "react";
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  Circle,
  useMapEvents,
} from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

// Reliable CDN Icon Assets
const DefaultIcon = L.icon({
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
});
L.Marker.prototype.options.icon = DefaultIcon;

const jobIcon = L.icon({
  iconUrl: "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-red.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
});

// Environment-agnostic backend base URL configuration
const API_BASE_URL = import.meta.env?.VITE_API_BASE_URL || "http://localhost:8000";

// SUB-COMPONENT: Listens for map clicks and fires the API payload
function MapClickHandler({ onMapClick }) {
  useMapEvents({
    click: (e) => {
      onMapClick([e.latlng.lat, e.latlng.lng]);
    },
  });
  return null;
}

function MainMap() {
  const [workerPos, setWorkerPos] = useState([27.7172, 85.324]); // Kathmandu center
  const [radius, setRadius] = useState(5000); // UI visual helper (meters)
  const [jobTag, setJobTag] = useState("plumber");

  // States to hold the real response coming back from FastAPI
  const [job, setJob] = useState(null);
  const [isMatch, setIsMatch] = useState(false);
  const [loading, setLoading] = useState(false);

  // THE LIVE NETWORK CONNECTION PIPELINE
  const handleMapClick = async (coords) => {
    setLoading(true);
    setJob({ pos: coords }); // Store location instantly to drop the pin

    try {
      const response = await fetch(`${API_BASE_URL}/api/jobs/match`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          title: "Live Map Job Request",
          tag: jobTag,
          latitude: coords[0], // Lat
          longitude: coords[1], // Long
        }),
      });

      const result = await response.json();

      if (result.status === "success" && result.total_matches > 0) {
        setIsMatch(true);
      } else {
        setIsMatch(false);
      }
    } catch (error) {
      console.error("Error matching job via backend:", error);
      setIsMatch(false);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ position: "relative", width: "100%", height: "100%" }}>
      
      {/* SIDE CONTROL PANEL */}
      <div
        style={{
          position: "absolute",
          top: "20px",
          right: "20px",
          zIndex: 1000,
          background: "white",
          padding: "15px",
          borderRadius: "8px",
          boxShadow: "0 2px 10px rgba(0,0,0,0.15)",
          fontFamily: "sans-serif",
          width: "260px",
        }}
      >
        <h4 style={{ margin: "0 0 5px 0" }}>Live PostGIS Sandbox</h4>
        <p style={{ fontSize: "11px", color: "#666", margin: "0 0 10px 0" }}>
          Your DB worker is hardcoded at center of blue circle with a 5km range.
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

        <hr style={{ margin: "15px 0" }} />

        {/* LIVE DATABASE FEEDBACK BOX */}
        <div
          style={{
            padding: "10px",
            borderRadius: "6px",
            backgroundColor: loading
              ? "#fef7e0"
              : job
                ? isMatch
                  ? "#e6f4ea"
                  : "#fce8e6"
                : "#f1f3f4",
          }}
        >
          <b
            style={{
              display: "block",
              color: loading
                ? "#b06000"
                : job
                  ? isMatch
                    ? "#137333"
                    : "#c5221f"
                  : "#5f6368",
            }}
          >
            {loading
              ? "Querying Postgres..."
              : job
                ? isMatch
                  ? "LIVE DB MATCH FOUND!"
                  : "NO MATCH IN DATABASE"
                : "Click map to query..."}
          </b>
          {job && !loading && (
            <span style={{ fontSize: "11px", display: "block", marginTop: "5px", color: "#555" }}>
              Lat: {job.pos[0].toFixed(4)} | Long: {job.pos[1].toFixed(4)}
            </span>
          )}
        </div>
      </div>

      {/* LEAFLET CANVAS MAP LAYER */}
      <MapContainer center={workerPos} zoom={13} scrollWheelZoom={true}>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        <MapClickHandler onMapClick={handleMapClick} />

        {/* Static Database Worker Visual Pin Reference */}
        <Marker position={workerPos}>
          <Popup>
            <b>Worker Record #1 (Saved in DB)</b>
            <br />
            Skills: Plumber
          </Popup>
        </Marker>

        {/* Static Database Worker 5km Visual Radius Reference */}
        <Circle
          center={workerPos}
          radius={radius}
          pathOptions={{
            color: "#1a73e8",
            fillColor: "#1a73e8",
            fillOpacity: 0.1,
          }}
        />

        {/* Real-time Job Pin (Always renders on click, popup changes dynamically) */}
        {job && !loading && (
          <Marker position={job.pos} icon={jobIcon}>
            <Popup>
              <div style={{ fontFamily: "sans-serif" }}>
                <strong>Client Job Request</strong>
                <br />
                Category: {jobTag}
                <br />
                <b style={{ color: isMatch ? "#137333" : "#c5221f" }}>
                  {isMatch ? "✓ PostGIS Match Verified" : "✗ DB Mismatch / Out of Range"}
                </b>
              </div>
            </Popup>
          </Marker>
        )}
      </MapContainer>
    </div>
  );
}

export default MainMap;
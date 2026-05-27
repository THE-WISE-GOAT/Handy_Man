import React, { useState } from 'react';
import { MapContainer, TileLayer, Marker, Circle } from 'react-leaflet';

// Explicit fix for the default map pin icons in React
import L from 'leaflet';
import markerIcon from 'leaflet/dist/images/marker-icon.png';
import markerShadow from 'leaflet/dist/images/marker-shadow.png';
let DefaultIcon = L.icon({
    iconUrl: markerIcon,
    shadowUrl: markerShadow,
    iconSize: [25, 41],
    iconAnchor: [12, 41]
});
L.Marker.prototype.options.icon = DefaultIcon;

function App() {
  // Center coordinates (latitude, longitude)
  const workerLocation = [27.7172, 85.3240]; 
  
  // Service radius state (starts at 5000 meters / 5km)
  const [radius, setRadius] = useState(5000); 

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', fontFamily: 'sans-serif' }}>
      
      {/* Control Dashboard Overlay */}
      <div style={{ padding: '20px', background: '#f4f4f4', zIndex: 1000, boxShadow: '0 2px 5px rgba(0,0,0,0.1)' }}>
        <h2>Worker Map Dashboard</h2>
        <label>
          <strong>Service Radius:</strong> {(radius / 1000).toFixed(1)} km
        </label>
        <br />
        <input 
          type="range" 
          min="1000" 
          max="20000" 
          step="1000"
          value={radius} 
          onChange={(e) => setRadius(Number(e.target.value))}
          style={{ width: '300px', marginTop: '10px', cursor: 'pointer' }}
        />
      </div>

      {/* The Map Framework Container */}
      <MapContainer 
        center={workerLocation} 
        zoom={12} 
        style={{ flex: 1, width: '100%' }}
      >
        {/* Fetching standard visual background tiles from OpenStreetMap */}
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        />

        {/* Worker Position Pin */}
        <Marker position={workerLocation} />

        {/* The Scalable Service Zone Circle */}
        <Circle 
          center={workerLocation} 
          radius={radius} 
          pathOptions={{ color: 'blue', fillColor: 'blue', fillOpacity: 0.15 }} 
        />
      </MapContainer>
    </div>
  );
}

export default App;
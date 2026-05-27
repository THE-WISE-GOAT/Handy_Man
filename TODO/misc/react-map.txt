Perfect. Your project layout is completely clean and empty (just those placeholder `.gitkeep` files). This is the absolute best place to start.

Based on our plan, we should build the **React map interface (Frontend)** first. It gives you an immediate visual win so you can physically see the worker's red dot and radius circle right on your screen.

Since `frontend/worker_app` is completely empty right now, we need to generate the basic React files inside it first before adding the map.

Here is exactly how to set up the map interface from scratch:

---

### Step 1: Open Your Terminal & Navigate

Make sure you are inside your integrated VS Code terminal. Type this command to move directly into your empty worker app folder:

```bash
cd frontend/worker_app

```

### Step 2: Initialize the React Files

Since the folder already exists, we will initialize a fresh Vite + React setup directly inside it. Run this command:

```bash
npm create vite@latest . -- --template react

```

*(Note: The `.` tells Vite to install the files right inside your current `worker_app` folder instead of creating a new one).*

If it asks to clear or proceed, type `y` and hit **Enter**.

### Step 3: Install the Core Tools & Map Libraries

Now, download your React files along with the **Frame (Leaflet)** library we discussed:

```bash
npm install
npm install leaflet react-leaflet

```

*(Your `worker_app` folder will instantly fill with files like `index.html` and a `src` folder).*

### Step 4: Add the Visual Map Styles (`index.html`)

Leaflet needs its design sheet so the background grid aligns perfectly.

1. In your VS Code sidebar, look inside `frontend/worker_app` and open **`index.html`**.
2. Paste this single line inside the `<head>` tags:

```html
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />

```

3. Save the file (**Ctrl + S**).

### Step 5: Write the Map Interface Code (`src/App.jsx`)

Now we combine the frame (Leaflet) with the street pictures (OpenStreetMap).

1. In the sidebar, expand `src` and open **`App.jsx`**.
2. Erase everything inside it and paste this exact clean map setup:

```jsx
import React, { useState } from 'react';
import { MapContainer, TileLayer, Marker, Circle } from 'react-leaflet';

// Fixed setup for default map pin icons in React
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

```

3. Save the file (**Ctrl + S**).

---

### Step 6: Launch and Verify

Type this final command into your terminal to boot up the local preview:

```bash
npm run dev

```

Ctrl + click the link it gives you (like `http://localhost:5173`). You should see your interactive worker map live in your browser! Let me know if it loads smoothly.
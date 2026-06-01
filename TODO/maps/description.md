Here is the exact, 100% free tech stack you should use for your gig-worker map app.

### The Recommended Free Map Stack

* **1. The Map Code (Frontend):** React Leaflet
* **2. The Map Pictures (Tiles):** OpenStreetMap (OSM)
* **3. The Database (Backend):** PostgreSQL with PostGIS
* **4. The Live Updates:** Socket.io

---

### Why These Specific Tools? (Key Points)

**1. React Leaflet (The UI)**

* **What it does:** It provides the interactive map area on your website.
* **Why use it:** It is completely free and built exactly for React. It handles the user dragging the map, dropping the red dot (worker location), and drawing the circle (working radius).

**2. OpenStreetMap (The Visuals)**

* **What it does:** It provides the actual images of the streets, buildings, and cities.
* **Why use it:** Google Maps and Mapbox will charge you money once you get enough users. OpenStreetMap is public and free forever. You plug OSM's URL directly into your React Leaflet code.

**3. PostgreSQL + PostGIS (The Brain)**

* **What it does:** It stores your user data and performs the heavy map math.
* **Why use it:** Standard databases are bad at maps. The **PostGIS** extension is specifically designed for spatial math. When a customer posts a job, PostGIS instantly calculates exactly which workers have a radius overlapping that specific job location.

<!-- **4. Socket.io (The Live Connection)**

* **What it does:** It keeps the frontend and backend connected in real-time.
* **Why use it:** When a customer posts a job, the worker's map needs to update instantly without them refreshing the page. Socket.io pushes that new job marker directly to the Leaflet map. -->
<!-- connect through fastapi -->

---

### How They All Work Together (The Flow)

1. **Setup:** The worker opens the app. **React Leaflet** loads the map, using **OpenStreetMap** to show the streets.
2. **Define Zone:** The worker drops their pin and sets a 5km radius. This location data is saved in **PostgreSQL**.
3. **New Job:** A customer posts a plumbing job across town.
4. **The Match:** **PostGIS** calculates the math and confirms the job falls inside the worker's 5km circle.
5. **The Alert:** **Socket.io** instantly sends a ping to the worker's app, and **React Leaflet** draws a new job marker on their screen.

Would you like to focus on setting up the React map interface first, or should we design the database tables needed for the radius matching?
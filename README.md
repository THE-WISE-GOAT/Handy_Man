# Handy_Man: A Highly Localized, Multi-Tier Gig Economy Marketplace

`Handy_Man` is a location-centric, map-based digital platform that bridges the gap between independent gig workers, professional service organizations, and local customers. Unlike rigid on-demand apps with algorithmic pricing, this platform empowers workers with total geographic control via interactive service radius mapping and facilitates direct, transparent price negotiations.

The application dynamically accommodates diverse hiring scenarios—ranging from single ad-hoc repairs to multi-worker modular groups and blueprint-reliant agency projects.

---

## 🚀 Core Features

### 📍 Visual Map-Based Worker Dashboard

* **Dynamic Geofencing:** Workers appear as a node on an interactive map UI and can visually adjust a slider to establish a custom service radius zone.
* **Real-time Job Pinning:** Nearby consumer tasks matching the worker's skills materialize as pin points on the map, providing instant visibility into local demand.

### 💼 Flexible Multi-Tier Hiring Models

1. **Single Independent Worker:** Traditional one-to-one hiring for explicit tasks (e.g., a quick pet checkup or emergency electrical fix).
2. **Modular Worker Groups:** Customers can bundle multiple independent workers for scaled jobs requiring minimal inter-coordination (e.g., hiring three separate painters to coat a house concurrently).
3. **Professional Organizations:** Direct contractual routing to local shops and agencies for jobs requiring structural blueprints and deep inter-team synchronization (e.g., full-scale copper plumbing installation).

### 🤖 Intelligent AI/ML Tag Matching

* **Automated Semantic Analysis:** An underlying NLP processor parses raw, conversational user problem descriptions (e.g., *"My floorboards are warped and leaking water"*), extracting precise operational identifiers like `#plumbing` and `#flooring` to match relevant specialists automatically.
* **Smart Recommendations:** Ranks and recommends workers by applying weighting constraints to proximity vectors, consumer ratings, completion histories, and preliminary estimates.

### 💬 Open-Market Negotiation Engine

* **Bidding Pipeline:** Eliminates opaque corporate price-fixing. Workers evaluate incoming job requirements and submit initial quotes directly to customers.
* **Real-time Chat:** An integrated message layer allows both parties to discuss material costs (e.g., paint choices or wiring types) and lock down a mutually agreed-upon contract.

---

## 🏗️ System Architecture & Tech Stack

The architecture follows an decoupled, event-driven Monorepo layout using a standard Client-Server pipeline:

```text
                           +--------------------------+
                           |  Frontend Applications   |
                           |   (Flutter / React Native) |
                           +------------+-------------+
                                        |
                         REST APIs      |     WebSockets
                        (HTTP Requests) |    (Real-time Chat)
                                        v
                           +------------+-------------+
                           |     Backend Services      |
                           |    (FastAPI / Node.js)   |
                           +------------+-------------+
                                        |
                           Geospatial   |   Relational
                           Queries      |   Data Queries
                                        v
                           +------------+-------------+
                           |    PostgreSQL + PostGIS  |
                           |    Distributed Database  |
                           +--------------------------+

```

### 🛠️ Technical Stack Specifications

* **Frontend UI:** Cross-platform Mobile/Web framework utilizing **Mapbox API** or **Google Maps API** for custom spatial overlays and drag-and-drop boundary radiuses.
* **Backend Framework:** Async architecture capable of high-throughput connection pooling to handle real-time geolocation streaming.
* **Geospatial Engine:** **PostgreSQL with PostGIS extensions**, utilizing indexed spatial metrics to query point-in-radius overlaps under $200\text{ms}$.
* **Real-Time Data Pipeline:** **WebSockets** for atomic message transport and push-notification routing during live contract bidding.

---

## 📁 Repository Directory Blueprint

```text
📁 Handy_Man/
│
├── 📁 .github/workflows/       # Automated CI/CD integration tests
├── 📁 docs/                    # University proposal, database schemas, UML sequence diagrams
│
├── 📁 backend/                 # API Application Source Code
│   ├── 📁 src/
│   │   ├── 📁 api/             # Routes (Authentication, Jobs, Bids, Tag Management)
│   │   ├── 📁 core/            # System configuration, security profiles, and AI modules
│   │   ├── 📁 models/          # Relational database entities and Object-Relational Mapping (ORM)
│   │   └── 📁 services/        # Geospatial lookup tables and recommendation algorithms
│   └── 📄 Dockerfile           # Elastic Container configuration for AWS deployment
│
├── 📁 frontend/                # Cross-platform client workspace
│   ├── 📁 user_app/            # Unified customer + worker React application
│   └── 📁 shared/              # Common UI design atomic modules, routes, and API clients
│
├── 📁 database/                # Database configurations
│   └── 📄 schema.sql           # PostGIS geographical initialization script
│
├── 📄 .gitignore               # System variable file protection (.env blocklist)
└── 📄 README.md                # Comprehensive project reference layout

```

---

## 🛠️ Preliminary Installation & Local Setup

### 1. Prerequisites

Ensure you have the following environments configured globally:

* Node.js (v18+) or Python (3.10+)
* PostgreSQL (v14+) with the `PostGIS` extension installed locally
* API access tokens for Mapbox or Google Maps Platform

### 2. Database Initialization

Spin up a local PostgreSQL instance and execute the spatial index configurations:

```bash
# Enter your database terminal
psql -U your_username -d your_database -f database/schema.sql

```

### 3. Environment Environment Configuration

Create a `.env` file within the `backend/` folder following this framework:

```env
DATABASE_URL=postgresql://username:password@localhost:5432/handyman_db
MAPS_API_KEY=your_secret_maps_token
JWT_SECRET=your_secure_authentication_secret_string

```

### 4. Booting the Application

Navigate into the backend target folder, fetch dependencies, and start the development engine:

```bash

cd backend
npm install   # or pip install -r requirements.txt
npm start     # or uvicorn src.core.main:app --reload

```
end.

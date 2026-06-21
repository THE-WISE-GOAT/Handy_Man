# Handy_Man Project Status

## Overview

Handy_Man is a location-aware gig marketplace that connects local customers with independent service workers through a map-centric experience. The current repository contains a backend API, two React-based frontend applications (customer and worker), shared UI and API utilities, and database models for geospatial worker matching.

## What is implemented

### Backend
- FastAPI application entrypoint in `backend/src/core/main.py` with CORS and router registration.
- Authentication and authorization:
  - `backend/src/core/router/auth.py`: user registration with password hashing and default customer role assignment.
  - `backend/src/core/router/login.py`: login endpoint using OAuth2 password flow and JWT token issuance.
- Worker management:
  - `backend/src/core/router/worker.py`: worker role application endpoint.
- Service task flow:
  - `backend/src/core/router/service_task.py`: create service tasks, fetch current user tasks, query available workers by geospatial radius, and logout placeholder.
- Database and models:
  - `backend/src/core/model.py`: SQLAlchemy models for `User`, `Role`, `UserRole`, `Worker`, `Service_tasks`, `Chat_logs`, and `Bids`.
  - `backend/src/core/schema.py`: Pydantic request/response models for user creation, token payloads, worker onboarding, and customer problem extraction.
  - `backend/src/database/database.py`: database engine, session factory, and dependency generator using environment configuration.

### Frontend
- `frontend/customer_app`:
  - `src/App.jsx`: routes for home, login, signup, and protected customer dashboard.
  - `src/pages/Customer_Dashboard.jsx`: customer-facing dashboard with tabbed booking UI, chat-style problem capture, AI-style tag extraction, task loading, and a worker role application button.
- `frontend/worker_app`:
  - `src/App.jsx`: protected worker route and cross-app navigation to the customer application.
  - `src/pages/Worker_Dashboard.jsx`: worker dashboard UI with online/offline toggle, live dispatch mockup, schedule queue, and link to a map sandbox.
- Shared frontend utilities:
  - `frontend/shared/api/client.js`: reusable API client with auth header injection, JSON parsing, and normalized errors.
  - `frontend/shared/components` and route wrappers for protected and anonymous routes.

### Project documentation and structure
- `README.md`: contains an architecture overview, feature summary, and repo structure.
- `TODO/maps/db-setup.md`: database setup guidance for spatial tables.

## Pending work

### Backend remaining tasks
- Persist worker profile details after role application and complete worker onboarding endpoints.
- Implement actual chat endpoint(s) and store chat logs in `Chat_logs`.
- Build bid submission, bid status management, and worker selection workflow.
- Add full JWT validation and the `get_current_user` logic for secure endpoints.
- Harden validation, error handling, and edge-case response behavior.
- Add automated tests for API routes and model behavior.

### Frontend remaining tasks
- Replace current mock UI data with live backend data and authenticated session state.
- Connect login/signup flows to the backend auth API.
- Implement the customer service request submission flow and worker matching UI.
- Add real map integration for worker radius, task pinning, and geospatial visual overlays.
- Build chat and negotiation UI for customer-worker conversations and bid exchange.
- Align environment variables across `frontend/customer_app`, `frontend/worker_app`, and shared config.

### Database and deployment
- Create or migrate PostgreSQL/PostGIS schema for the application models.
- Add geographic indexes and ensure geospatial queries are production-ready.
- Seed sample workers, tasks, and roles for local development.
- Add Docker and `docker-compose` deployment support for backend, frontend, and database services.
- Configure production-safe CORS, secrets, and environment file handling.

## Summary

The repository currently has a strong scaffolded implementation for user onboarding, worker role activation, service task creation, and customer/worker frontend shells. The next key work is to wire the frontend to the backend, complete worker profile and bidding flows, add chat/notification support, and make the geospatial matching features fully operational.

Discuss the extent to which you believe that you have a motivation problem as a software engineer.
Given what you have learned in this chapter, design a plan to increase motivation of employees to provide prompt service to customers working in a software development company.
Design a plan to increase the motivation of the system administrator even when the supervisor is not monitoring your work.

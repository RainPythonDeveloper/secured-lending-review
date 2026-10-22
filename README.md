# Finance Hackathon - TBC Open Banking Proxy Server

A NestJS-based proxy service designed to securely interact with the TBC Bank Mock Open Banking API (/0.8/v1/accounts), featuring built-in Swagger documentation and full Docker containerization.

---

## Tech Stack

- Framework: NestJS (TypeScript)
- HTTP Client: @nestjs/axios
- Documentation: @nestjs/swagger
- Containerization: Docker & Docker Compose

---

## Project Structure

FINANCE-HACKATHON/
├── docker-compose.yml       # Root orchestration file
└── server/                  # Backend application
    ├── Dockerfile           # Multi-stage production Dockerfile
    ├── dockerignore         # Files to ignore in Docker build
    ├── package.json         # Dependencies and scripts
    └── src/
        └── account/         # Accounts controller, service, and DTOs

---

## Getting Started

### Prerequisites

Ensure you have the following installed on your machine:
- Docker & Docker Compose
- Node.js (v20+ recommended, for local development)

---

### Method 1: Running with Docker (Recommended)

To run the server containerized using Docker Compose from the project root:

1. Open your terminal in the project root directory (finance-hackathon).
2. Build and start the services in detached mode:
   docker compose up --build -d
3. View container logs:
   docker compose logs -f
4. Stop the containers when needed:
   docker compose down

---

### Method 2: Running Locally (Development Mode)

If you want to run the NestJS server natively on your machine:

1. Navigate to the server folder:
   cd server
2. Install dependencies:
   npm install
3. Start the application in watch/development mode:
   npm run start:dev

---

## API Documentation (Swagger)

Once the application is up and running, open your browser and navigate to the interactive Swagger UI:

- URL: http://localhost:3000/api/docs

The Swagger interface comes pre-configured with default mock headers and parameters for the TBC Bank Open Banking API, allowing you to test endpoints instantly.
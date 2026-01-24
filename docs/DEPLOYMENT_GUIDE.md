# Deployment Guide

This guide outlines the steps to deploy the JWHD IP Automation application (Backend and Frontend) to a production environment.

## Prerequisites

*   A **MongoDB Atlas** cluster (or any MongoDB instance reachable by the backend).
*   A **Google Cloud Platform (GCP)** project with:
    *   **Google Cloud Storage** bucket created.
    *   A **Service Account** with `Storage Object Admin` role.
    *   A JSON key file for the Service Account.
    *   **Gemini API** enabled and an API key generated.
*   A **Vercel** account (recommended for frontend) or any Node.js hosting.
*   A cloud provider for the backend (e.g., AWS EC2, Google Cloud Run, Heroku, DigitalOcean, or Azure).

---

## 1. Backend Deployment

The backend is a FastAPI application. It can be deployed using Docker or directly on a VM/container service.

### Environment Variables

Ensure the following environment variables are set in your production environment:

| Variable | Description | Example |
| :--- | :--- | :--- |
| `MONGODB_URL` | Connection string for MongoDB. | `mongodb+srv://user:pass@cluster.mongodb.net/?retryWrites=true&w=majority` |
| `SECRET_KEY` | Secret key for JWT token generation. | `openssl rand -hex 32` output |
| `GOOGLE_APPLICATION_CREDENTIALS_JSON` | Content of the GCP Service Account JSON key. | `{"type": "service_account", ...}` |
| `GCP_BUCKET_NAME` | Name of the GCS bucket for file storage. | `jwhd-ip-automation-prod` |
| `GOOGLE_API_KEY` | API Key for Google Gemini. | `AIzaSy...` |
| `GEMINI_MODEL` | Gemini model version to use. | `gemini-2.0-flash-exp` |

**Important:** For `GOOGLE_APPLICATION_CREDENTIALS_JSON`, paste the *entire content* of the JSON file as a string.

### Deployment Steps (Generic)

1.  **Clone the Repository:**
    ```bash
    git clone <repository_url>
    cd backend
    ```

2.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Run with Gunicorn (Production Server):**
    Install Gunicorn: `pip install gunicorn`
    Run the app:
    ```bash
    gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:8000
    ```

### Deployment Steps (Docker)

1.  Create a `Dockerfile` in the `backend` directory:
    ```dockerfile
    FROM python:3.9
    WORKDIR /code
    COPY ./requirements.txt /code/requirements.txt
    RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt
    COPY ./app /code/app
    CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]
    ```

2.  Build and Run:
    ```bash
    docker build -t jwhd-backend .
    docker run -d -p 80:80 --env-file .env jwhd-backend
    ```

---

## 2. Frontend Deployment

The frontend is a Next.js application. The recommended deployment platform is **Vercel**.

### Environment Variables

| Variable | Description | Example |
| :--- | :--- | :--- |
| `NEXT_PUBLIC_API_URL` | URL of the deployed backend API. | `https://api.jwhd-automation.com/api/v1` |

### Deployment Steps (Vercel)

1.  **Push Code to GitHub/GitLab/Bitbucket.**
2.  **Import Project in Vercel:**
    *   Select the repository.
    *   Set the **Root Directory** to `frontend`.
    *   The **Build Command** (`next build`) and **Output Directory** (`.next`) should be auto-detected.
3.  **Configure Environment Variables:**
    *   Add `NEXT_PUBLIC_API_URL` pointing to your deployed backend URL.
4.  **Deploy:** Click "Deploy". Vercel will build and host the application.

### Deployment Steps (Node.js Server)

1.  **Build the Application:**
    ```bash
    cd frontend
    npm install
    npm run build
    ```

2.  **Start the Server:**
    ```bash
    npm start
    ```
    The app will typically run on port 3000.

---

## 3. Post-Deployment Verification

1.  **Seed Initial User:**
    Once the backend is live, you need to create the first user. You can do this via a script or a temporary endpoint if enabled.
    *   **Option A (Script):** Run `python seed_user.py` locally, pointing to the production MongoDB URL.
    *   **Option B (Endpoint):** Use the `/api/v1/auth/seed-user` endpoint if it's exposed (secure this!).

2.  **Test Login:**
    Go to the frontend URL and attempt to log in with the seeded credentials.

3.  **Test E2E Flow:**
    *   Upload a dummy PDF application.
    *   Verify data is extracted.
    *   Generate an ADS.
    *   Download the generated files.
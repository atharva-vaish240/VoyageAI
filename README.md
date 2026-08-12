# ✈️ VoyageAI

> An AI-powered travel planning application that creates personalized itineraries based on your preferences, trip details, and destination.

VoyageAI is a full-stack travel planning platform designed to simplify trip planning by combining user preferences, AI-generated itineraries, destination imagery, maps, and Google Calendar integration into a single application.

Instead of manually researching destinations, activities, food, and schedules, users can provide their trip requirements and let VoyageAI generate a structured itinerary tailored to them.

---

## ✨ Features

### 🔐 Authentication & User Management
- User registration and login
- JWT-based authentication
- Access and refresh tokens
- Protected API routes
- User-specific data isolation
- Google OAuth authentication

### 🧑‍💻 Travel Preferences
Users can define preferences such as:
- Food preferences
- Drinking preferences
- Travel style
- Accommodation preferences

These preferences are used when generating personalized itineraries.

### 🗺️ Trip Management
Users can:
- Create trips
- View their trips
- Update trip details
- Delete trips
- Specify destination and travel dates
- Specify number of travellers
- Define budget
- Add special requirements

### 🤖 AI-Powered Itinerary Generation
VoyageAI integrates Google's Gemini API to generate structured travel itineraries based on:
- Destination
- Trip duration
- Number of travellers
- Budget
- User travel preferences
- Special requirements

Generated itineraries are persisted in the database so they can be accessed later.

### 📍 Destination Information
VoyageAI integrates external services to provide destination-related information and imagery, including:
- Pexels for destination images
- OpenStreetMap / Nominatim for geocoding
- Overpass API for OpenStreetMap-based location data

### 📅 Google Calendar Integration
Users can connect their Google Calendar and add itinerary activities to their calendar.

OAuth credentials are handled server-side and stored securely.

### 📱 Responsive Frontend
The frontend is built with React and TypeScript and provides:
- Authentication flows
- Trip dashboard
- Trip creation
- AI itinerary generation
- Itinerary viewing
- Google Calendar integration
- Responsive UI

---

## 🏗️ Tech Stack

### Frontend
- React
- TypeScript
- Vite
- Axios

### Backend
- Python
- FastAPI
- SQLAlchemy
- Alembic
- Pydantic
- JWT
- Authlib

### Database
- PostgreSQL

### AI & External APIs
- Google Gemini API
- Google OAuth 2.0
- Google Calendar API
- Pexels API
- OpenStreetMap / Nominatim
- Overpass API

### Testing
- Pytest
- Vitest

### Deployment
- Render

---

## 🏛️ Architecture

```text
                         ┌──────────────────────┐
                         │      VoyageAI        │
                         │      Frontend        │
                         │  React + TypeScript  │
                         │        + Vite        │
                         └──────────┬───────────┘
                                    │
                              REST API / JWT
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │      FastAPI         │
                         │       Backend        │
                         └──────────┬───────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              │                     │                     │
              ▼                     ▼                     ▼
       ┌─────────────┐       ┌─────────────┐       ┌─────────────┐
       │ PostgreSQL  │       │ Gemini API  │       │ Google APIs │
       │             │       │             │       │             │
       │ Users       │       │ Itinerary   │       │ OAuth       │
       │ Preferences │       │ Generation  │       │ Calendar    │
       │ Trips       │       └─────────────┘       └─────────────┘
       └─────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    ▼                               ▼
             ┌─────────────┐                ┌─────────────┐
             │   Pexels    │                │ OpenStreetMap│
             │ Destination │                │  / Nominatim │
             │   Images    │                │   / Overpass │
             └─────────────┘                └─────────────┘
```

---

# 🚀 Getting Started

## Prerequisites

Make sure you have the following installed:

- Git
- Python 3.11+
- Node.js 18+
- npm
- PostgreSQL

You will also need API credentials for the external services you want to use.

---

## 1. Clone the Repository

```bash
git clone https://github.com/atharva-vaish240/VoyageAI.git
cd VoyageAI
```

---

# ⚙️ Backend Setup

Navigate to the backend:

```bash
cd backend
```

### Create a virtual environment

Linux/macOS:

```bash
python3 -m venv venv
source venv/bin/activate
```

Windows:

```powershell
python -m venv venv
venv\Scripts\activate
```

### Install dependencies

```bash
pip install -r requirements.txt
```

---

## 2. Configure Environment Variables

Create a `.env` file inside the `backend` directory:

```bash
touch .env
```

Example:

```env
DATABASE_URL=postgresql://USERNAME:PASSWORD@localhost:5432/voyageai

JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

CORS_ORIGINS=http://localhost:5173

GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

GOOGLE_REDIRECT_URI=http://localhost:5173/auth/google/callback
GOOGLE_BACKEND_CALLBACK=http://localhost:8000/api/v1/oauth/google/callback

GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-3.5-flash

GOOGLE_API_KEY=your-google-api-key

PEXELS_API_KEY=your-pexels-api-key

NOMINATIM_BASE_URL=https://nominatim.openstreetmap.org
OVERPASS_API_URL=https://overpass-api.de/api/interpreter

SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
EMAIL_FROM=your-email@gmail.com
EMAIL_FROM_NAME=VoyageAI
```

> **Never commit `.env` or real API credentials to Git.**
>
> Use `.env.example` as a template and keep actual credentials in your local environment or deployment platform's secret/environment-variable manager.

---

# 🗄️ Database Setup

Create a PostgreSQL database:

```sql
CREATE DATABASE voyageai;
```

Make sure your `DATABASE_URL` points to it.

Then run the Alembic migrations:

```bash
alembic upgrade head
```

Check the migration state with:

```bash
alembic current
```

---

# ▶️ Run the Backend

From the `backend` directory:

```bash
uvicorn app.main:app --reload
```

The API will be available at:

```text
http://localhost:8000
```

FastAPI's interactive API documentation is available at:

```text
http://localhost:8000/docs
```

---

# 🎨 Frontend Setup

Open another terminal:

```bash
cd frontend
```

Install dependencies:

```bash
npm install
```

Create the frontend environment file:

```bash
touch .env
```

Set the backend API URL:

```env
VITE_API_BASE_URL=http://localhost:8000
```

Start the development server:

```bash
npm run dev
```

The frontend will typically be available at:

```text
http://localhost:5173
```

---

# 🔑 Google OAuth Setup

Google OAuth requires configuring an OAuth client in Google Cloud.

For local development, configure the following redirect URI:

```text
http://localhost:8000/api/v1/oauth/google/callback
```

and the frontend callback:

```text
http://localhost:5173/auth/google/callback
```

For production, replace these with your deployed frontend/backend URLs.

> Never commit the Google OAuth client secret to the repository.

---

# 🤖 Gemini Setup

VoyageAI uses Google's Gemini API to generate structured travel itineraries.

Create a Gemini API key and add it to:

```env
GEMINI_API_KEY=your-gemini-api-key
```

The model can be configured through:

```env
GEMINI_MODEL=gemini-3.5-flash
```

---

# 📅 Google Calendar Setup

Google Calendar integration requires OAuth credentials with Calendar API access.

The application uses the authenticated user's Google account to:

1. Request Calendar authorization
2. Receive an authorization code
3. Exchange the code server-side
4. Securely store the required credentials
5. Create calendar events from itinerary activities

Google credentials should always be stored as environment variables.

---

# 🧪 Running Tests

### Backend

From `backend`:

```bash
pytest
```

### Frontend

From `frontend`:

```bash
npm run test
```

If the frontend has a build script configured, verify the production build with:

```bash
npm run build
```

---

# 🌐 Deployment

VoyageAI can be deployed as separate frontend and backend services.

A typical deployment architecture is:

```text
              Internet
                  │
                  ▼
       ┌─────────────────────┐
       │      Frontend       │
       │ React + Vite        │
       │      Render         │
       └──────────┬──────────┘
                  │
                  │ HTTPS API requests
                  ▼
       ┌─────────────────────┐
       │       Backend       │
       │ FastAPI + Uvicorn   │
       │      Render         │
       └──────────┬──────────┘
                  │
                  ▼
       ┌─────────────────────┐
       │     PostgreSQL      │
       │       Render        │
       └─────────────────────┘
```

### Backend build/start configuration

A typical backend start command:

```bash
alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

### Frontend

Build the frontend:

```bash
npm run build
```

Configure the deployed frontend to use the deployed backend:

```env
VITE_API_BASE_URL=https://your-backend-url
```

Production environment variables should be configured through the hosting provider rather than committed to Git.

---

# 🔒 Security

VoyageAI handles authentication and third-party integrations, so credentials must be handled carefully.

### Never commit:

- `.env`
- JWT secrets
- Google OAuth client secrets
- Gemini API keys
- Pexels API keys
- SMTP passwords
- Database passwords
- Any other private credentials

Use:

```text
.env.example
```

only for documenting the **names and format** of required variables.

---

# 📁 Project Structure

```text
VoyageAI/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── v1/
│   │   ├── core/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── main.py
│   │
│   ├── migrations/
│   │   └── versions/
│   │
│   ├── tests/
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/
│   ├── src/
│   ├── public/
│   ├── package.json
│   └── .env.example
│
└── README.md
```

---

# 🔄 Core Application Flow

```text
User
 │
 ▼
Register / Login
 │
 ▼
Set Travel Preferences
 │
 ▼
Create Trip
 │
 ├── Destination
 ├── Dates
 ├── Travellers
 ├── Budget
 └── Special Requirements
 │
 ▼
VoyageAI Backend
 │
 ▼
Gemini AI
 │
 ▼
Structured Itinerary
 │
 ▼
Persisted in PostgreSQL
 │
 ├── View itinerary
 ├── Destination information
 └── Add activities to Google Calendar
```

---

# 🛡️ Authentication & User Isolation

VoyageAI uses JWT-based authentication with access and refresh tokens.

Protected resources are associated with the authenticated user.

For example:

```text
User A
  │
  ├── Trip 1
  └── Trip 2

User B
  │
  ├── Trip 3
  └── Trip 4
```

User A cannot access User B's trips through the API.

---

# 🧩 API

The backend exposes RESTful API endpoints through FastAPI.

Once the backend is running, explore the complete API interactively at:

```text
http://localhost:8000/docs
```

The OpenAPI specification is automatically generated by FastAPI.

---

# 🛠️ Development Workflow

A recommended development workflow:

```bash
# Backend
cd backend
source venv/bin/activate
uvicorn app.main:app --reload

# Frontend
cd frontend
npm run dev
```

When modifying database models:

```bash
alembic revision --autogenerate -m "describe migration"
alembic upgrade head
```

Always review autogenerated migrations before committing them.

---

# 🚧 Future Improvements

Potential future improvements include:

- More advanced itinerary customization
- Hotel and flight integrations
- Real-time travel information
- Weather-aware itinerary planning
- Collaborative trip planning
- More sophisticated map integration
- Improved itinerary regeneration
- Offline itinerary access
- More granular AI personalization

---

# 🌐 Live Demo

**Frontend:** https://voyageai-1zzx.onrender.com

**Backend API:** https://voyageai-backend-kovu.onrender.com

**API Documentation:** https://voyageai-backend-kovu.onrender.com/docs

---

# 📸 Screenshots

<!-- Add polished screenshots here -->

---

# 👨‍💻 Author

**Atharva Vaish**

Computer Science student and developer interested in full-stack development, AI, open source, and competitive programming.

---

# 📄 License

Add your preferred license here.

For example:

```text
MIT License
```

if this project is released under the MIT License.

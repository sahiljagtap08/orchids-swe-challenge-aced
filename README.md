# 🌸 PetalClone - Vision-Powered AI Website Cloner (completed in 12 hrs including documentation)

PetalClone is an advanced AI-powered tool that clones websites with exceptional visual and structural accuracy. It leverages a vision-capable AI agent, a robust browser automation backend, and a real-time frontend to deconstruct, understand, and recreate websites from just a URL.

The system goes beyond simple HTML scraping. It uses a headless browser to capture a pixel-perfect screenshot and render JavaScript, then feeds this visual information to a multi-step AI agent. The agent analyzes the layout and style like a human developer would, ensuring the final clone is a high-fidelity replica of the original.

![PetalClone UI](frontend/public/screenshot.png)
## ✨ Core Features

-   **Vision-Powered Cloning**: Uses GPT-4 Vision and a sophisticated prompt strategy to analyze screenshots for pixel-perfect layout, color, and typography replication.
-   **Full Website Cloning**: Discovers and clones an entire website by crawling all internal links up to a specified page limit.
-   **Robust Scraping Engine**: Built with **Playwright** to handle modern, JavaScript-heavy websites, capturing not just HTML but also computed styles and high-resolution screenshots.
-   **Real-Time Progress**: The UI features a live log stream (via SSE) that shows the agent's progress, from crawling and scraping to AI-powered code generation.
-   **Interactive Results View**: A resizable multi-panel interface allows you to compare the original screenshot, the live preview, and the generated code side-by-side.
-   **Asset Handling**: Downloads all site assets (CSS, JS, images) and rewrites links for a fully self-contained, offline-ready clone.
-   **Downloadable Archives**: Packages the entire cloned site into a convenient `.zip` file for download.
-   **Multi-Model Support**: Easily configurable to use different large language models (e.g., Claude 3.5 Sonnet, GPT-4o, Gemini).

## 🏗️ Technical Architecture

PetalClone consists of a FastAPI backend that orchestrates the cloning process and a Next.js frontend that provides a rich, interactive user experience.

1.  **Job Request**: The user submits a URL through the Next.js frontend.
2.  **Orchestration**: The FastAPI backend kicks off a cloning job.
3.  **Site Crawling (Full Site Mode)**: A `SiteCrawler` discovers all accessible pages on the target domain.
4.  **Scraping**: The `PlaywrightScraper` service launches a headless browser for each page, executing JavaScript and taking a full-page screenshot.
5.  **AI Vision Cloning**: The `VisionCloner` service sends the screenshot and scraped HTML/CSS to the selected LLM. A sophisticated, multi-step prompt guides the AI to:
    a.  Deconstruct the page into logical components.
    b.  Extract a design system (colors, fonts).
    c.  Generate a pixel-perfect HTML clone with embedded CSS.
6.  **Live Logging**: Throughout the process, the backend streams logs to the frontend via Server-Sent Events (SSE).

### 🥞 Tech Stack

| Component      | Technology                                                              | Purpose                                                 |
| -------------- | ----------------------------------------------------------------------- | ------------------------------------------------------- |
| **Frontend**   | Next.js (App Router), React, TypeScript, Tailwind CSS, Shadcn UI        | Modern, interactive, real-time UI                       |
| **Backend**    | FastAPI, Python, Uvicorn                                                | High-performance API server and job orchestration       |
| **Scraping**   | Playwright                                                              | Robust, headless browser automation for accurate scraping |
| **AI Models**  | GPT-4 Vision, Claude 3.5 Sonnet, Gemini                                 | Core intelligence for code generation and analysis      |
| **Real-time**  | Server-Sent Events (SSE)                                                | Unidirectional event stream for live logging            |
| **UI Layout**  | `react-resizable-panels`                                                | Interactive, resizable panels for the results view      |

## 🚀 Getting Started

### Prerequisites

-   Python 3.10+
-   Node.js 20+ and `npm`
-   **API Keys** for the LLM providers (e.g., OpenAI) and **Hyperbrowser**.

### 1. Backend Setup

First, set up and run the FastAPI server.

```bash
# Navigate to the backend directory
cd backend

# Create a virtual environment and activate it
python -m venv .venv
source .venv/bin/activate #make sure you activate it before installing 
# On Windows: .\.venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

pip install playwright

# Install Playwright's browser dependencies (one-time setup)
playwright install --with-deps

# Create the environment file for API keys
# Create a new file named .env in the `backend/` directory
# and add your keys.
touch .env
```

Your `backend/.env` file should contain the keys for the services you want to use. The vision-powered agent relies on a model like GPT-4o, and the premium fallback scraper requires Hyperbrowser.

```env
# backend/.env

# Required for vision-powered cloning
OPENAI_API_KEY="sk-..."

# Required for the premium fallback scraper to handle difficult sites
HYPERBROWSER_API_KEY="..."

# Optional keys for other models
ANTHROPIC_API_KEY="sk-ant-..."
GOOGLE_AI_API_KEY="..."
```

Now, run the backend server:

```bash
# Start the FastAPI server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The backend API will be available at `http://localhost:8000`.

### 2. Frontend Setup

In a separate terminal, set up and run the Next.js frontend.

```bash
# Navigate to the frontend directory
cd frontend

# Install Node.js dependencies
npm install

# Run the development server
npm run dev
```

### 3. Access the Application

Open your browser and navigate to **[http://localhost:3000](http://localhost:3000)** to use PetalClone.

## 📝 Project Structure

```
orchids-challenge/
├── backend/
│   ├── app/
│   │   ├── core/         # Configuration and settings
│   │   ├── models/       # Pydantic data models
│   │   ├── routers/      # API endpoints (FastAPI routers)
│   │   └── services/     # Core business logic (scraping, AI, logging)
│   ├── .env              # Environment variables for API keys (create this)
│   └── requirements.txt  # Python dependencies
├── frontend/
│   ├── public/           # Static assets
│   ├── src/
│   │   ├── app/          # Next.js App Router pages
│   │   ├── components/   # Reusable React components (including Shadcn UI)
│   │   └── lib/          # Helper functions and API client
│   └── package.json      # Node.js dependencies
└── README.md
```

---

*Built for the Orchids SWE Internship Challenge.*

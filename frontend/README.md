# Employer Chat Interface MVP (LearnerOS Talent Intelligence)

A minimalist, responsive conversational AI interface built with React, Next.js (App Router), and Tailwind CSS for the **Employer Talent Intelligence** platform.

The interface enables hiring managers and talent partners to investigate candidate competencies, review verified evidence from learner memory cards, benchmark technical leadership, and initiate new candidate evaluations.

---

## Key Features

- **Two-Pane Responsive Layout:** Fixed/slide-over navigation sidebar paired with a flexible, auto-scrolling chat window optimized across desktop, tablet, and mobile viewports.
- **Session Management:** Browse past candidate investigation threads with timestamps and category tags, dynamically updating the active thread on selection.
- **New Chat Flow:** Dedicated "New Investigation" action that clears active dialogue and readies prompt input while preserving previous session history without state leakage.
- **Visual Distinction & Markdown Support:** Aligned user prompts and assistant intelligence reports with support for headers, lists, code blocks, tables, copy-to-clipboard, and match score badges.
- **Simulated Response Engine:** Realistic response generation simulating candidate investigations across backend architecture, graph databases, MLOps/AI agents, and technical leadership benchmarks.
- **Architecturally Decoupled Data Layer:** Clean abstraction separating message dispatch, session state, and mock datasets (`src/data/mockConversations.ts` & `src/services/chatService.ts`) from presentation components for zero-rewrite future backend API integration.

---

## Project Structure

```text
frontend/
├── src/
│   ├── app/
│   │   ├── globals.css              # Global styles, Tailwind imports, custom scrollbar
│   │   ├── layout.tsx               # Root layout with metadata and dark theme
│   │   └── page.tsx                 # Main view coordinating state and service calls
│   ├── components/
│   │   ├── Sidebar.tsx              # Session navigation, filtering, and New Chat trigger
│   │   ├── ChatWindow.tsx           # Active message thread, starter prompts, input bar
│   │   └── MessageItem.tsx          # Distinct user/assistant cards with markdown & copy
│   ├── data/
│   │   └── mockConversations.ts     # Standalone mock datasets simulating candidate queries
│   ├── services/
│   │   └── chatService.ts           # Decoupled service layer for session/message operations
│   └── types/
│       └── chat.ts                  # TypeScript definitions for messages, sessions, metadata
├── package.json
├── tsconfig.json
└── README.md
```

---

## Prerequisites

- **Node.js**: `v18.18.0` or later (tested on `v26.x`)
- **Package Manager**: `npm` (v9+) or `yarn` (v1.22+)

---

## Installation & Local Execution

### 1. Navigate to the Frontend Directory

```bash
cd frontend
```

### 2. Install Dependencies

Using `npm`:
```bash
npm install
```

Or using `yarn`:
```bash
yarn install
```

### 3. Start the Development Server

Using `npm`:
```bash
npm run dev
```

Or using `yarn`:
```bash
yarn dev
```

The application will be available at [http://localhost:3000](http://localhost:3000).

---

## Production Build & Linting

To verify TypeScript types and generate the optimized production build:

```bash
npm run build
```

To run ESLint:

```bash
npm run lint
```

```

To run ESLint:

```bash
npm run lint
```

To run the automated verification test suite:

```bash
npm test
```

---

## Environment Variables

The frontend is configured via environment variables with sensible defaults:

| Variable | Description | Default |
| :--- | :--- | :--- |
| `NEXT_PUBLIC_API_URL` | Base URL of the LearnerOS FastAPI backend REST service | `http://localhost:8010` |
| `NEXT_PUBLIC_DEMO_USER_ID` | Fallback user ID for unauthenticated / offline evaluation previews | `1` |

To override, create `.env.local` in `frontend/`:
```env
NEXT_PUBLIC_API_URL=http://localhost:8010
NEXT_PUBLIC_DEMO_USER_ID=1
```

---

## Authentication & Live Agent Chat Integration (Task 21)

The frontend integrates client authentication and connects the chat interface to live backend services:

- **Auth Service (`src/services/authService.ts`):** Decoupled service managing `POST /auth/signup` and `POST /auth/signin`.
- **JWT State Management (`src/contexts/AuthContext.tsx`):** Centralized `AuthProvider` that persists access tokens across sessions (`sessionStorage` / `localStorage`), decodes user credentials, and triggers automatic sign-out on HTTP 401 Unauthorized responses.
- **Route Protection (`src/middleware.ts` & client guards):** Edge middleware and client-side guards redirect unauthenticated visits to `/` to `/signin`, and redirect authenticated visits to `/signin` and `/signup` back to `/`.
- **User-Scoped Conversations:** The sidebar and chat window query `GET /users/{user_id}/conversations` and `POST /users/{user_id}/conversations` using the authenticated user's ID with `Authorization: Bearer <access_token>` headers.
- **Live Agent Message Dispatch:** Dispatches prompts to `POST /conversations/{conversation_id}/chat` with Bearer authentication, seamlessly falling back to `POST /conversations/{conversation_id}/messages` and labeled previews if the live agent is offline.
- **Visual Artifact Rendering (`src/components/VisualArtifactRenderer.tsx`):** Renders SVGs, image cards, and visual containers returned in agent payloads cleanly alongside text responses, featuring interactive SVG preview/source toggling, responsive auto-scaling, and clipboard copy.


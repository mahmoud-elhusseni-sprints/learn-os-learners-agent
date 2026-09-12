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

---

## Decoupled Architecture & Live API Integration

The application follows strict architectural separation:

- **Presentation (`src/components/`):** React components are pure view layers receiving data and firing callbacks.
- **State Management (`src/app/page.tsx`):** Coordinates sessions and message threads without embedding mock data logic.
- **Service Layer (`src/services/chatService.ts`):** Exposes `getSessions()`, `getSessionById()`, `createSession()`, and `sendMessage()`.

When the backend conversation endpoints (e.g. FastAPI / Neo4j agent endpoints) are ready, simply replace the internal logic in `chatService.ts` with standard `fetch()` or `axios` HTTP calls matching the same TypeScript interface contracts.

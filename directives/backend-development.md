---
name: backend-development
description: Backend and server-side development skill covering Node.js, Python (Flask/FastAPI/Django), REST APIs, authentication, middleware, and server logic. Use this skill when the user wants to build a server, write backend code, create API endpoints, handle user authentication, set up routes, work with sessions/cookies, build a CRUD app, or connect a backend to a database or frontend. Also use for tasks like "build me a login system", "create a REST API", "set up Express", "write a Flask route", or "make a backend for my app". Triggers even for partial tasks like writing a single route, middleware function, or auth flow.
---

# Backend Development Skill

This skill covers building robust, secure, and maintainable server-side applications across popular backend stacks.

---

## Step 1: Clarify the Project

Before starting, identify:
- **Language/Framework**: Node.js (Express/Fastify)? Python (Flask/FastAPI/Django)? Other?
- **Purpose**: REST API? Web server with SSR? Microservice? Full-stack monolith?
- **Auth**: Does this need login/signup? Sessions? JWT?
- **Database**: SQL (PostgreSQL, MySQL, SQLite) or NoSQL (MongoDB, Redis)?
- **Deployment target**: Local dev only? Cloud (Render, Railway, Vercel, AWS)?

If no preference, default to **Node.js + Express** for JS projects, **FastAPI** for Python projects.

---

## Step 2: Project Structure

### Node.js / Express
```
project/
├── src/
│   ├── routes/         # Route handlers
│   ├── controllers/    # Business logic
│   ├── middleware/     # Auth, validation, error handling
│   ├── models/         # DB models / schemas
│   ├── services/       # External integrations, reusable logic
│   └── app.js          # App setup
├── .env
├── package.json
└── server.js           # Entry point
```

### Python / FastAPI
```
project/
├── app/
│   ├── routers/        # Route definitions
│   ├── models/         # Pydantic + DB models
│   ├── services/       # Business logic
│   ├── dependencies/   # Auth, DB session injection
│   └── main.py         # FastAPI app setup
├── .env
└── requirements.txt
```

---

## Step 3: Express Quick Setup

```js
// server.js
import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import userRoutes from './src/routes/users.js';

dotenv.config();

const app = express();
app.use(cors());
app.use(express.json());

app.use('/api/users', userRoutes);

app.use((err, req, res, next) => {
  console.error(err.stack);
  res.status(500).json({ error: 'Internal Server Error' });
});

app.listen(process.env.PORT || 3000, () => {
  console.log('Server running on port 3000');
});
```

---

## Step 4: FastAPI Quick Setup

```python
# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import users, items

app = FastAPI(title="My API")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

app.include_router(users.router, prefix="/api/users")
app.include_router(items.router, prefix="/api/items")
```

---

## Step 5: REST API Design Principles

- Use **nouns** for resources, not verbs: `/api/users` not `/api/getUsers`
- Use HTTP methods correctly:
  - `GET` → read data
  - `POST` → create new resource
  - `PUT/PATCH` → update resource
  - `DELETE` → remove resource
- Return appropriate HTTP status codes:
  - `200 OK`, `201 Created`, `204 No Content`
  - `400 Bad Request`, `401 Unauthorized`, `403 Forbidden`, `404 Not Found`
  - `500 Internal Server Error`
- Always return JSON with a consistent shape
- Version your API: `/api/v1/users`

---

## Step 6: Authentication Patterns

### JWT (Stateless)
Best for: APIs consumed by mobile apps or SPAs
```js
import jwt from 'jsonwebtoken';

// Sign token on login
const token = jwt.sign({ userId: user.id }, process.env.JWT_SECRET, { expiresIn: '7d' });

// Verify in middleware
function authMiddleware(req, res, next) {
  const token = req.headers.authorization?.split(' ')[1];
  if (!token) return res.status(401).json({ error: 'Unauthorized' });
  try {
    req.user = jwt.verify(token, process.env.JWT_SECRET);
    next();
  } catch {
    res.status(401).json({ error: 'Invalid token' });
  }
}
```

### Sessions (Stateful)
Best for: Traditional web apps with server-rendered pages
```js
import session from 'express-session';

app.use(session({
  secret: process.env.SESSION_SECRET,
  resave: false,
  saveUninitialized: false,
  cookie: { secure: process.env.NODE_ENV === 'production', httpOnly: true }
}));
```

### Password Hashing (always use bcrypt)
```js
import bcrypt from 'bcrypt';

// Hash on signup
const hashed = await bcrypt.hash(password, 12);

// Verify on login
const match = await bcrypt.compare(password, hashed);
```

---

## Step 7: Input Validation

Never trust user input. Always validate and sanitize.

### Express + Zod
```js
import { z } from 'zod';

const createUserSchema = z.object({
  email: z.string().email(),
  password: z.string().min(8),
  name: z.string().min(1).max(100),
});

function validate(schema) {
  return (req, res, next) => {
    const result = schema.safeParse(req.body);
    if (!result.success) return res.status(400).json({ errors: result.error.errors });
    req.body = result.data;
    next();
  };
}
```

### FastAPI (built-in with Pydantic)
```python
from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str

@router.post("/")
async def create_user(user: UserCreate):  # Auto-validates!
    ...
```

---

## Step 8: Error Handling

Centralize error handling. Don't let errors leak stack traces to clients.

```js
// Express global error handler (last middleware)
app.use((err, req, res, next) => {
  const status = err.status || 500;
  const message = process.env.NODE_ENV === 'production' 
    ? 'Something went wrong' 
    : err.message;
  res.status(status).json({ error: message });
});

// Async wrapper to catch errors without try/catch everywhere
const asyncHandler = fn => (req, res, next) => Promise.resolve(fn(req, res, next)).catch(next);
```

---

## Step 9: Security Checklist

- [ ] Passwords hashed with bcrypt (cost factor ≥ 10)
- [ ] JWT secrets stored in `.env`, not in code
- [ ] HTTPS enforced in production
- [ ] Rate limiting on auth endpoints (`express-rate-limit`)
- [ ] CORS configured to specific origins in production
- [ ] SQL queries use parameterized statements (never string interpolation)
- [ ] Helmet.js set security headers (Express)
- [ ] Input validation on all user-facing routes
- [ ] Sensitive data never logged

---

## Step 10: Environment Variables

```bash
# .env
PORT=3000
DATABASE_URL=postgresql://user:password@localhost:5432/mydb
JWT_SECRET=your-very-long-random-secret
NODE_ENV=development
```

Always add `.env` to `.gitignore`. Provide a `.env.example` with placeholder values.

---

## Reference Files

- `references/databases.md` — ORM setup (Prisma, SQLAlchemy, Mongoose)
- `references/deployment.md` — Deploy to Render, Railway, Fly.io

---

## Output Format

Provide complete, runnable code with:
- All imports and setup included
- `.env.example` if environment variables are used
- Brief explanation of the architecture choices
- `package.json` / `requirements.txt` dependencies listed

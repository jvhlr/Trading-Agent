---
name: web-development
description: Full-stack web development skill covering HTML, CSS, JavaScript, and modern frameworks. Use this skill whenever the user wants to build a website, web app, landing page, portfolio, or any browser-based project — including tasks like "make a webpage", "build a site", "create a form", "add interactivity", "make it responsive", or "turn this design into code". Also triggers for framework-specific work (React, Vue, Next.js, Tailwind), accessibility fixes, SEO optimization, and performance tuning. Use this even for partial tasks like writing a nav bar, fixing a broken layout, or adding dark mode.
---

# Web Development Skill

This skill covers the full spectrum of web development — from simple static pages to dynamic, interactive web apps — with an emphasis on clean, maintainable, production-quality code.

---

## Step 1: Understand the Project

Before writing a single line of code, clarify:

- **Type**: Static site? SPA? Server-rendered? Landing page? Dashboard?
- **Stack**: Plain HTML/CSS/JS? React? Vue? Next.js? Tailwind? No preference?
- **Audience**: Who uses this, and on what devices?
- **Goal**: Is this for learning, portfolio, production deployment, or a demo?

If the user hasn't specified, make a reasonable choice and state it clearly.

---

## Step 2: Choose the Right Stack

| Use Case | Recommended Stack |
|---|---|
| Simple static page / portfolio | HTML + CSS + Vanilla JS |
| Component-heavy UI | React + Tailwind CSS |
| Full-stack app | Next.js (React) or Nuxt.js (Vue) |
| Fast prototype / landing page | HTML + Tailwind CDN |
| Interactive data dashboard | React + Recharts or Chart.js |
| Form-heavy app | React Hook Form or native HTML5 |

---

## Step 3: Project Structure

### For Plain HTML/CSS/JS:
```
project/
├── index.html
├── css/
│   └── style.css
├── js/
│   └── main.js
└── assets/
    └── images/
```

### For React (Vite):
```
project/
├── public/
├── src/
│   ├── components/
│   ├── pages/
│   ├── hooks/
│   ├── utils/
│   └── App.jsx
├── index.html
└── package.json
```

---

## Step 4: HTML Best Practices

- Always use **semantic HTML**: `<header>`, `<nav>`, `<main>`, `<section>`, `<article>`, `<footer>`
- Every image must have a descriptive `alt` attribute
- Use `<label>` for all form inputs (link via `for`/`id`)
- Declare `lang` on `<html>`: `<html lang="en">`
- Use `<meta name="description">` for SEO
- Avoid `<div>` soup — reach for semantic elements first

```html
<!-- Bad -->
<div class="header">
  <div class="nav">...</div>
</div>

<!-- Good -->
<header>
  <nav aria-label="Main navigation">...</nav>
</header>
```

---

## Step 5: CSS Best Practices

- Use **CSS custom properties** (variables) for colors, spacing, and fonts
- Mobile-first responsive design with `min-width` media queries
- Use **Flexbox** for 1D layouts, **CSS Grid** for 2D layouts
- Avoid magic numbers — use spacing scales (4px, 8px, 16px, 24px, 32px, 48px, 64px)
- Name classes by purpose, not appearance (`.card--highlighted` not `.card--red`)

```css
:root {
  --color-primary: #2563eb;
  --color-bg: #f9fafb;
  --font-body: 'Inter', sans-serif;
  --spacing-md: 1rem;
  --radius-md: 0.5rem;
}

/* Mobile first */
.grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: var(--spacing-md);
}

@media (min-width: 768px) {
  .grid {
    grid-template-columns: repeat(3, 1fr);
  }
}
```

---

## Step 6: JavaScript Best Practices

- Use `const` by default, `let` only when reassignment is needed; avoid `var`
- Prefer `addEventListener` over inline `onclick`
- Use **async/await** for asynchronous code; always handle errors with try/catch
- Avoid DOM manipulation inside loops — build strings or fragments first
- Keep functions small and single-purpose

```js
// Bad
document.getElementById('btn').onclick = function() { ... }

// Good
document.getElementById('btn').addEventListener('click', handleClick);

async function handleClick() {
  try {
    const data = await fetchData('/api/items');
    renderItems(data);
  } catch (err) {
    showError('Failed to load items.');
  }
}
```

---

## Step 7: Responsive Design Checklist

- [ ] Works on 320px (small phone) up to 1440px+ (desktop)
- [ ] Text is readable without zooming (min 16px body)
- [ ] Touch targets are at least 44x44px
- [ ] Images use `max-width: 100%` and `height: auto`
- [ ] Navigation collapses on mobile (hamburger or simplified)
- [ ] No horizontal overflow on small screens

---

## Step 8: Accessibility (A11y) Checklist

- [ ] All interactive elements are keyboard-navigable
- [ ] Focus states are visible (don't remove `outline` without a replacement)
- [ ] Color contrast ratio is at least 4.5:1 for normal text
- [ ] Modals trap focus and close on Escape
- [ ] Use `aria-label` / `aria-describedby` where needed
- [ ] Skip-to-content link for keyboard users

---

## Step 9: Performance Tips

- Compress images (use `.webp` format when possible)
- Lazy-load images below the fold: `loading="lazy"`
- Minify CSS/JS in production
- Use `font-display: swap` for web fonts
- Avoid render-blocking scripts — use `defer` or `async`
- Prefer CSS transitions over JS-driven animations

---

## Step 10: Common Patterns

### Sticky Navbar
```css
nav {
  position: sticky;
  top: 0;
  z-index: 100;
  background: white;
  box-shadow: 0 1px 4px rgba(0,0,0,0.1);
}
```

### Card Grid
```css
.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 1.5rem;
}
```

### Centered Hero Section
```css
.hero {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 2rem;
}
```

### Dark Mode (CSS only)
```css
@media (prefers-color-scheme: dark) {
  :root {
    --color-bg: #0f172a;
    --color-text: #f1f5f9;
  }
}
```

---

## Reference Files

- `references/frameworks.md` — Setup guides for React, Vue, Next.js
- `references/tailwind.md` — Tailwind utility class patterns
- `references/accessibility.md` — Deeper accessibility guidance

---

## Output Format

Deliver complete, runnable code. Unless told otherwise:
- Single-file HTML for simple pages
- Multi-file structure for larger projects (explain the structure)
- Add comments to explain non-obvious choices
- Include instructions to run/open if relevant

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Purpose

This workspace produces **scroll-driven animated websites** — typically from a video source — using vanilla HTML/CSS/JS, GSAP, and Lenis. No bundler, no framework. All output is a self-contained static site served locally for review.

## WAT Framework

You operate inside the **WAT framework** (Workflows, Agents, Tools):

- **Workflows** (`workflows/`) — Markdown SOPs defining the objective, inputs, tools to invoke, and edge cases. Read before acting. Don't create or overwrite workflows without being asked.
- **Agents (you)** — Orchestrate; don't execute everything directly. Read the relevant workflow, call the right tools, recover from errors, update workflows when you learn something new.
- **Tools** (`tools/`) — Python scripts for deterministic execution. Check `tools/` before writing a new script.

Credentials go in `.env` only. Temporary files go in `.tmp/` (disposable). Final outputs live in cloud services.

## Skills

Two skills are available in `Skills/`. Invoke them when relevant:

| Skill | Trigger | File |
|-------|---------|------|
| `frontend-design` | Any request to build a UI component, page, or interface | `Skills/Frontend_Design/SKILL.md` |
| `video-to-website` | Turning a video file into a scroll-driven animated website | `Skills/Video_to_Website/SKILL.md` |

Both skills are often used together: `video-to-website` drives the overall workflow; `frontend-design` drives creative and aesthetic decisions within it.

## Tech Stack (Scroll-Driven Sites)

- **Vanilla HTML/CSS/JS** — no bundler, no framework
- **GSAP + ScrollTrigger** — animation engine and scroll binding
- **Lenis** — smooth scroll wrapper (mandatory — replaces native scroll feel)
- **FFmpeg/FFprobe** — video analysis and frame extraction (must be on PATH)
- **CDN delivery** — all libraries loaded via CDN at end of `<body>`, in this order:
  1. `lenis@1`
  2. `gsap@3`
  3. `gsap@3/ScrollTrigger`
  4. `js/app.js`

## Local Development

Serve the output directory over HTTP (frames won't load over `file://`):

```bash
npx serve .
# or
python -m http.server 8000
```

No build step. Edit files and refresh.

## Output Structure (per project)

```
project-root/
  index.html
  css/style.css
  js/app.js
  frames/frame_0001.webp ...
```

## Key Architecture Invariants

These apply to every scroll-driven site produced here. Violations break the aesthetic contract:

- **No glassmorphism cards** — text sits directly on the background; hierarchy is font size/weight/color only
- **Side-aligned text only** — all sections use `.align-left` or `.align-right` (outer 40% zones); centered text only for stats with a full dark overlay
- **No consecutive repeated animations** — each `data-animation` type must differ from its neighbors
- **Counter animations** — all numbers count up from 0 via GSAP; never appear statically
- **Lenis is mandatory** — `lenis.on("scroll", ScrollTrigger.update)` must be wired before any ScrollTrigger
- **Frame rendering** — use padded cover mode with `IMAGE_SCALE` 0.82–0.90; never pure `Math.max` (clips into header) or pure `Math.min` (visible seam)
- **CTA section** — mark with `data-persist="true"` so it stays visible at end of scroll
- **Total scroll height** — minimum 800vh for 6 sections; hero gets 20%+ of scroll range

## Self-Improvement Loop

When something breaks: fix the tool → verify it works → update the relevant workflow with what you learned. The workflow is the lasting artifact, not the fix.

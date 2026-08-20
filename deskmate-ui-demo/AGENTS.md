# Prototype Instructions

Run the local server yourself and open the preview in the browser available to this environment. Do not give the user server-start instructions when you can run it.

Before making substantial visual changes, use the Product Design plugin's `get-context` skill when the visual source is unclear or no longer matches the current goal. When the user gives durable prototype-specific design feedback, preferences, or decisions, record them in `AGENTS.md`.

When implementing from a selected generated mock, treat that image as the source of truth for layout, component anatomy, density, spacing, color, typography, visible content, and hierarchy.

Build app UI in `src/`. Keep `.openai/hosting.json`, `worker/index.js`, `scripts/prepare-sites-build.mjs`, and `tests/sites-worker.test.mjs` intact so the same local prototype can be handed to Sites. Before a Sites handoff, run `npm run build` and `npm run test:sites`; the build must leave `dist/client/index.html`, `dist/server/index.js`, and `dist/.openai/hosting.json`.

## DeskMate visual and product decisions

- Desktop-first application; target design viewport is 1440 × 1024, with responsive support down to tablet/mobile widths.
- Use a deep graphite navigation rail and a light warm-gray/white workspace. Accent colors are cyan and cobalt blue; green, amber, and red are reserved for semantic status.
- The interface should feel futuristic and premium while remaining restrained, spacious, and easy for beginners.
- Preserve EasyInput capabilities: voice recording, history, vocabulary/replacement rules, key mapping, microphone source, Wi-Fi, startup sound, AI assistant status, shortcuts, formatting, account, and diagnostics.
- Add DeskMate capabilities: virtual pet dashboard, expression library/editor, motion choreography, environmental sensors, device connection, and Codex/Claude Code/Hermes/Workbody adapters.
- Hardware and firmware protocol features that are not implemented must be visibly marked as demo data or pending integration.
- Use Noto Sans SC / system Chinese sans-serif for Chinese and Inter-style sans-serif for Latin/numerals.

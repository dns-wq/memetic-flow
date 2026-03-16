#!/usr/bin/env python3
"""
Capture screenshots from the Memetic Flow demo site for README documentation.

Captures hero screenshots and animated GIF from the demo-site (Vue static app)
at localhost:4000 or the live GitHub Pages site. Injects light-mode CSS for
better visibility in README images.

Requires: pip install playwright && playwright install chromium

Usage:
    python scripts/capture_demo_screenshots.py [--url http://localhost:4000/memetic-flow]
"""

from __future__ import annotations

import argparse
import asyncio
import shutil
import subprocess
import sys
from pathlib import Path

OUTPUT_DIR = Path("docs/screenshots")
GIF_DIR = Path("docs/gifs")

# Light-mode CSS injected into the page before screenshots
LIGHT_MODE_CSS = """
/* ===== Global ===== */
body {
  background: #ffffff !important;
  color: #24292f !important;
}
::-webkit-scrollbar-track { background: #eaeef2 !important; }
::-webkit-scrollbar-thumb { background: #afb8c1 !important; }

/* ===== Demo Player ===== */
.demo-player { background: #ffffff !important; }

.dp-header {
  background: #f6f8fa !important;
  border-bottom-color: #d0d7de !important;
}
.dp-header .brand { color: #0969da !important; }
.dp-header .separator { color: #57606a !important; }
.dp-header .demo-title { color: #24292f !important; }
.dp-header .demo-stats { color: #656d76 !important; }
.dp-header .mode-badge {
  background: #ddf4ff !important;
  color: #0969da !important;
}
.dp-header .scenario-select {
  background: #f6f8fa !important;
  border-color: #d0d7de !important;
  color: #24292f !important;
}

/* ===== Right panel ===== */
.right-panel {
  border-left-color: #d0d7de !important;
  background: #ffffff !important;
}
.rp-tabs { border-bottom-color: #d0d7de !important; }
.rp-tab { color: #656d76 !important; }
.rp-tab.active { color: #0969da !important; border-bottom-color: #0969da !important; }
.rp-tab:hover { color: #24292f !important; }

.scenario-info {
  background: #f6f8fa !important;
  border-color: #d0d7de !important;
}
.scenario-info h3 { color: #24292f !important; }
.scenario-info .source { color: #656d76 !important; }
.scenario-info .description { color: #424a53 !important; }

/* ===== Metrics dashboard ===== */
.metrics-dashboard {
  background: #f6f8fa !important;
}
.chart-card {
  background: #ffffff !important;
  border-color: #d0d7de !important;
}
.chart-card .chart-title { color: #24292f !important; }
.chart-card .chart-value { color: #0969da !important; }

/* ===== Graph panel ===== */
.dynamics-graph-panel {
  background: #f6f8fa !important;
}

/* ===== Tooltip ===== */
.tooltip {
  background: rgba(255, 255, 255, 0.97) !important;
  border-color: #d0d7de !important;
  color: #24292f !important;
  box-shadow: 0 4px 12px rgba(0,0,0,0.12) !important;
}
.tooltip .tooltip-title { color: #24292f !important; }
.tooltip .tooltip-type { color: #656d76 !important; }
.tooltip .tooltip-desc { color: #424a53 !important; }
.tooltip .tooltip-goals { color: #424a53 !important; }
.tooltip .tooltip-state { color: #424a53 !important; }
.tooltip .state-label { color: #656d76 !important; }
.tooltip .state-value { color: #0969da !important; }

/* ===== Temporal slider ===== */
.temporal-slider {
  background: #f6f8fa !important;
  border-top-color: #d0d7de !important;
}
.temporal-slider .ctrl-btn {
  background: #f6f8fa !important;
  border-color: #d0d7de !important;
  color: #24292f !important;
}
.temporal-slider .ctrl-btn:hover { background: #eaeef2 !important; }
.temporal-slider .timestep-label { color: #656d76 !important; }
.temporal-slider .speed-select {
  background: #f6f8fa !important;
  border-color: #d0d7de !important;
  color: #24292f !important;
}
.temporal-slider input[type=range] { accent-color: #0969da !important; }

/* ===== Document viewer ===== */
.document-viewer {
  background: #f6f8fa !important;
  border-color: #d0d7de !important;
}
.doc-header {
  background: #eaeef2 !important;
  border-color: #d0d7de !important;
}
.doc-filename { color: #656d76 !important; }
.doc-source-link { color: #0969da !important; }
.doc-body { color: #24292f !important; }
.doc-body h3, .doc-body h4, .doc-body h5 { color: #24292f !important; }
.doc-body a { color: #0969da !important; }

/* ===== Landing page ===== */
.landing { background: #ffffff !important; }
.hero-tagline { color: #424a53 !important; }
.hero-sub { color: #656d76 !important; }
.feature-card {
  background: #f6f8fa !important;
  border-color: #d0d7de !important;
}
.feature-card h3 { color: #24292f !important; }
.feature-card p { color: #656d76 !important; }
.scenario-card {
  background: #f6f8fa !important;
  border-color: #d0d7de !important;
}
.scenario-card h3 { color: #24292f !important; }
.scenario-card p, .scenario-card .sc-meta { color: #656d76 !important; }
.mode-card {
  background: #f6f8fa !important;
  border-color: #d0d7de !important;
}
.footer { border-top-color: #d0d7de !important; color: #656d76 !important; }
"""

# JavaScript to patch canvas rendering colors for light mode
LIGHT_MODE_CANVAS_JS = """
(() => {
  // Patch DynamicsGraphPanel canvas colors
  // We override getContext to intercept fillStyle/strokeStyle assignments
  const darkToLight = {
    '#0d1117': '#f6f8fa',
    '#161b22': '#f6f8fa',
    '#1c2128': '#eaeef2',
    '#c9d1d9': '#24292f',   // node labels
    '#e6edf3': '#24292f',   // primary text
    '#8b949e': '#656d76',   // muted text
    '#484f58': '#8c959f',   // faint text / grid lines
    '#555': '#bbb',         // institution borders
    '#30363d': '#d0d7de',   // chart grid lines
  };

  // Store original getContext
  const origGetContext = HTMLCanvasElement.prototype.getContext;
  HTMLCanvasElement.prototype.getContext = function(type, attrs) {
    const ctx = origGetContext.call(this, type, attrs);
    if (type === '2d' && ctx && !ctx.__lightPatched) {
      ctx.__lightPatched = true;
      const origFillRect = ctx.fillRect.bind(ctx);

      // Proxy fillStyle
      let _fillStyle = ctx.fillStyle;
      Object.defineProperty(ctx, 'fillStyle', {
        get() { return _fillStyle; },
        set(v) {
          if (typeof v === 'string') {
            const lower = v.toLowerCase();
            _fillStyle = darkToLight[lower] || v;
          } else {
            _fillStyle = v;
          }
          // Apply through the native setter via a helper
          origGetContext.call(ctx.canvas, '2d').__proto__.__lookupSetter__('fillStyle').call(ctx, _fillStyle);
        }
      });

      // Proxy strokeStyle
      let _strokeStyle = ctx.strokeStyle;
      Object.defineProperty(ctx, 'strokeStyle', {
        get() { return _strokeStyle; },
        set(v) {
          if (typeof v === 'string') {
            const lower = v.toLowerCase();
            _strokeStyle = darkToLight[lower] || v;
          } else {
            _strokeStyle = v;
          }
          origGetContext.call(ctx.canvas, '2d').__proto__.__lookupSetter__('strokeStyle').call(ctx, _strokeStyle);
        }
      });
    }
    return ctx;
  };
})();
"""


async def _inject_light_mode(page) -> None:
    """Inject light-mode CSS and canvas color overrides."""
    await page.add_style_tag(content=LIGHT_MODE_CSS)
    # Force canvas re-render by briefly resizing
    await page.wait_for_timeout(200)


async def _zoom_to_fit(page) -> None:
    """Double-click canvas center to trigger zoom-to-fit."""
    canvas = await page.query_selector("canvas")
    if canvas:
        box = await canvas.bounding_box()
        if box:
            await page.mouse.dblclick(
                box["x"] + box["width"] / 2,
                box["y"] + box["height"] / 2,
            )
            await page.wait_for_timeout(800)


async def _scrub_timeline(page, progress: float) -> None:
    """Scrub timeline slider to given progress (0.0–1.0)."""
    await page.evaluate(f"""
        const slider = document.querySelector('input[type=range]');
        if (slider) {{
            const max = parseInt(slider.max) || 400;
            slider.value = Math.round(max * {progress});
            slider.dispatchEvent(new Event('input'));
        }}
    """)
    await page.wait_for_timeout(800)


async def _click_overview_tab(page) -> None:
    """Click the Overview tab so metrics dashboard is visible."""
    await page.evaluate("""
        const tabs = document.querySelectorAll('.rp-tab');
        for (const tab of tabs) {
            if (tab.textContent.trim() === 'Overview') {
                tab.click();
                break;
            }
        }
    """)
    await page.wait_for_timeout(500)


async def _switch_scenario(page, base_url: str, scenario: str) -> None:
    """Navigate to a specific scenario (hash-based routing)."""
    url = f"{base_url}/#/demo/{scenario}"
    await page.goto(url, wait_until="networkidle")
    await page.wait_for_selector("canvas", timeout=30000)
    await page.wait_for_timeout(4000)
    await _inject_light_mode(page)
    await _click_overview_tab(page)
    await _zoom_to_fit(page)


async def capture_all(base_url: str) -> None:
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("Error: playwright is required. Install with:")
        print("  pip install playwright && playwright install chromium")
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    GIF_DIR.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1920, "height": 1080})

        # --- Screenshot 1: AI Governance — hero force graph ---
        print("  Capturing hero_force_graph (AI Governance)...", end="", flush=True)
        try:
            await _switch_scenario(page, base_url, "ai_governance")
            await _scrub_timeline(page, 0.5)
            await _zoom_to_fit(page)
            await page.wait_for_timeout(1000)
            path = OUTPUT_DIR / "hero_force_graph.png"
            await page.screenshot(path=str(path), full_page=False)
            print(f" saved ({path.stat().st_size // 1024} KB)")
        except Exception as e:
            print(f" FAILED: {e}")

        # --- Screenshot 2: AI Governance — metrics dashboard ---
        print("  Capturing hero_metrics_dashboard (AI Governance @ 75%)...", end="", flush=True)
        try:
            await _scrub_timeline(page, 0.75)
            await page.wait_for_timeout(1000)
            path = OUTPUT_DIR / "hero_metrics_dashboard.png"
            await page.screenshot(path=str(path), full_page=False)
            print(f" saved ({path.stat().st_size // 1024} KB)")
        except Exception as e:
            print(f" FAILED: {e}")

        # --- Screenshot 3: Tech Startups — market dynamics ---
        print("  Capturing hero_tech_startups (Tech Startups)...", end="", flush=True)
        try:
            await _switch_scenario(page, base_url, "tech_startups")
            await _scrub_timeline(page, 0.8)
            await _zoom_to_fit(page)
            await page.wait_for_timeout(1000)
            path = OUTPUT_DIR / "hero_tech_startups.png"
            await page.screenshot(path=str(path), full_page=False)
            print(f" saved ({path.stat().st_size // 1024} KB)")
        except Exception as e:
            print(f" FAILED: {e}")

        # --- Screenshot 4: Chip Race — geopolitical dynamics ---
        print("  Capturing hero_chip_race (US-China Chip Race)...", end="", flush=True)
        try:
            await _switch_scenario(page, base_url, "chip_race")
            await _scrub_timeline(page, 0.6)
            await _zoom_to_fit(page)
            await page.wait_for_timeout(1000)
            path = OUTPUT_DIR / "hero_chip_race.png"
            await page.screenshot(path=str(path), full_page=False)
            print(f" saved ({path.stat().st_size // 1024} KB)")
        except Exception as e:
            print(f" FAILED: {e}")

        # --- Screenshot 5: Phase transition close-up (AI Governance final state) ---
        print("  Capturing hero_phase_transition (AI Governance final state)...", end="", flush=True)
        try:
            await _switch_scenario(page, base_url, "ai_governance")
            await _scrub_timeline(page, 1.0)
            await _zoom_to_fit(page)
            await page.wait_for_timeout(1000)
            path = OUTPUT_DIR / "hero_phase_transition.png"
            await page.screenshot(path=str(path), full_page=False)
            print(f" saved ({path.stat().st_size // 1024} KB)")
        except Exception as e:
            print(f" FAILED: {e}")

        # --- GIF capture (AI Governance timeline progression) ---
        frames_dir = GIF_DIR / "frames"
        frames_dir.mkdir(parents=True, exist_ok=True)

        num_frames = 40
        print(f"\n  Capturing {num_frames} GIF frames (AI Governance)...")
        try:
            await _switch_scenario(page, base_url, "ai_governance")

            for i in range(num_frames):
                progress = i / (num_frames - 1)
                await _scrub_timeline(page, progress)
                await page.wait_for_timeout(300)
                if i % 5 == 0:
                    await _zoom_to_fit(page)
                frame_path = frames_dir / f"frame_{i:03d}.png"
                await page.screenshot(path=str(frame_path), full_page=False)
                if i % 10 == 0:
                    print(f"    Frame {i}/{num_frames}...")

            print(f"  Captured {num_frames} frames")

            # Assemble GIF with ffmpeg
            gif_output = GIF_DIR / "simulation_replay.gif"
            if shutil.which("ffmpeg"):
                print("  Assembling GIF with ffmpeg...")
                palette_path = frames_dir / "palette.png"
                frame_pattern = str(frames_dir / "frame_%03d.png")

                subprocess.run([
                    "ffmpeg", "-y", "-framerate", "6",
                    "-i", frame_pattern,
                    "-vf", "fps=6,scale=960:-1:flags=lanczos,palettegen=stats_mode=diff",
                    str(palette_path),
                ], capture_output=True)

                subprocess.run([
                    "ffmpeg", "-y", "-framerate", "6",
                    "-i", frame_pattern,
                    "-i", str(palette_path),
                    "-filter_complex",
                    "fps=6,scale=960:-1:flags=lanczos[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle",
                    str(gif_output),
                ], capture_output=True)

                if gif_output.exists():
                    size_mb = gif_output.stat().st_size / (1024 * 1024)
                    print(f"  GIF assembled: {gif_output} ({size_mb:.1f} MB)")
                else:
                    print("  GIF assembly failed.")
            else:
                print("  ffmpeg not found — skipping GIF assembly.")

        except Exception as e:
            print(f"  Frame capture failed: {e}")

        await browser.close()
        print("\nDone!")


def main() -> None:
    parser = argparse.ArgumentParser(description="Capture demo site screenshots")
    parser.add_argument("--url", default="http://localhost:4000/memetic-flow",
                        help="Base URL of the demo site (default: http://localhost:4000/memetic-flow)")
    args = parser.parse_args()

    asyncio.run(capture_all(args.url))


if __name__ == "__main__":
    main()

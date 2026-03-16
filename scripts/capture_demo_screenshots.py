#!/usr/bin/env python3
"""
Capture screenshots from the Memetic Flow demo site for README documentation.

Captures hero screenshots and animated GIF from the demo-site (Vue static app)
at localhost:4000 or the live GitHub Pages site.

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

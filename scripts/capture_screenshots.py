#!/usr/bin/env python3
"""
Automated screenshot capture for Memetic Flow demo assets.

Captures hero screenshots and animated GIFs from the running demo site.
Requires: pip install playwright && playwright install chromium

Usage:
    python scripts/capture_screenshots.py [--url http://localhost:5173] [--output docs/screenshots]

The script navigates to each demo scenario, sets up specific views,
and captures screenshots at 1920x1080 resolution.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path


async def capture_all(base_url: str, output_dir: Path) -> None:
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("Error: playwright is required. Install with:")
        print("  pip install playwright && playwright install chromium")
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1920, "height": 1080})

        # --- Hero screenshots ---
        screenshots = [
            {
                "name": "hero_force_graph",
                "description": "Civilization from Scratch — 262 nodes self-organizing",
                "url": f"{base_url}/demo/civilization_from_scratch",
                "wait_for": ".dynamics-graph-panel canvas",
                "delay_ms": 5000,  # Let force sim settle + particles animate
            },
            {
                "name": "hero_metrics_dashboard",
                "description": "Social Media Regulation — polarization dynamics",
                "url": f"{base_url}/demo/social_media_regulation",
                "wait_for": ".dynamics-graph-panel canvas",
                "delay_ms": 5000,
            },
            {
                "name": "hero_ecosystem",
                "description": "Ecosystem Collapse — 85 species food web",
                "url": f"{base_url}/demo/ecosystem_collapse",
                "wait_for": ".dynamics-graph-panel canvas",
                "delay_ms": 5000,
            },
            {
                "name": "hero_ai_startup",
                "description": "AI Startup Ecosystem — market dynamics",
                "url": f"{base_url}/demo/ai_startup_ecosystem",
                "wait_for": ".dynamics-graph-panel canvas",
                "delay_ms": 5000,
            },
        ]

        for spec in screenshots:
            print(f"  Capturing {spec['name']}... ", end="", flush=True)
            try:
                await page.goto(spec["url"], wait_until="networkidle")
                await page.wait_for_selector(spec["wait_for"], timeout=30000)
                # Wait for force simulation to settle
                await page.wait_for_timeout(spec["delay_ms"])
                # Trigger zoom-to-fit via double-click on canvas
                canvas = await page.query_selector(".dynamics-graph-panel canvas")
                if canvas:
                    box = await canvas.bounding_box()
                    if box:
                        await page.mouse.dblclick(
                            box["x"] + box["width"] / 2,
                            box["y"] + box["height"] / 2,
                        )
                        await page.wait_for_timeout(500)
                path = output_dir / f"{spec['name']}.png"
                await page.screenshot(path=str(path), full_page=False)
                print(f"saved to {path}")
            except Exception as e:
                print(f"FAILED: {e}")

        # --- GIF capture (frame-by-frame for simulation replay) ---
        gif_dir = output_dir.parent / "gifs" / "frames"
        gif_dir.mkdir(parents=True, exist_ok=True)

        print("\n  Capturing simulation replay frames...")
        try:
            await page.goto(f"{base_url}/demo/civilization_from_scratch",
                            wait_until="networkidle")
            await page.wait_for_selector(".dynamics-graph-panel canvas", timeout=30000)
            await page.wait_for_timeout(5000)
            # Zoom to fit before capturing frames
            canvas = await page.query_selector(".dynamics-graph-panel canvas")
            if canvas:
                box = await canvas.bounding_box()
                if box:
                    await page.mouse.dblclick(
                        box["x"] + box["width"] / 2,
                        box["y"] + box["height"] / 2,
                    )
                    await page.wait_for_timeout(500)

            # Capture 30 frames across the timeline
            for i in range(30):
                progress = i / 29.0
                await page.evaluate(f"""
                    const slider = document.querySelector('.temporal-slider input[type=range]');
                    if (slider) {{
                        const max = parseInt(slider.max) || 400;
                        slider.value = Math.round(max * {progress});
                        slider.dispatchEvent(new Event('input'));
                    }}
                """)
                await page.wait_for_timeout(500)  # Allow snapshot fetch + render
                frame_path = gif_dir / f"frame_{i:03d}.png"
                await page.screenshot(path=str(frame_path), full_page=False)

            print(f"  Captured 30 frames to {gif_dir}")
            print("  Convert to GIF with:")
            print("    ffmpeg -framerate 5 -i frame_%03d.png -vf palettegen palette.png")
            print("    ffmpeg -framerate 5 -i frame_%03d.png -i palette.png -filter_complex paletteuse simulation_replay.gif")
        except Exception as e:
            print(f"  Frame capture failed: {e}")

        await browser.close()
        print("\nDone!")


def main() -> None:
    parser = argparse.ArgumentParser(description="Capture Memetic Flow screenshots")
    parser.add_argument("--url", default="http://localhost:3000",
                        help="Base URL of the running app (default: http://localhost:3000)")
    parser.add_argument("--output", default="docs/screenshots",
                        help="Output directory for screenshots (default: docs/screenshots)")
    args = parser.parse_args()

    asyncio.run(capture_all(args.url, Path(args.output)))


if __name__ == "__main__":
    main()

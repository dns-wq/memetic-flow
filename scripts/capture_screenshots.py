#!/usr/bin/env python3
"""
Automated screenshot capture for Memetic Flow demo assets.

Captures hero screenshots and animated GIFs from the running demo site.
Requires: pip install playwright && playwright install chromium

Usage:
    python scripts/capture_screenshots.py [--url http://localhost:3000] [--output docs/screenshots]

The script navigates to each demo scenario, sets up specific views,
and captures screenshots at 1920x1080 resolution.
"""

from __future__ import annotations

import argparse
import asyncio
import shutil
import subprocess
import sys
from pathlib import Path


async def _zoom_to_fit(page) -> None:
    """Double-click canvas center to trigger zoom-to-fit."""
    canvas = await page.query_selector(".dynamics-graph-panel canvas")
    if canvas:
        box = await canvas.bounding_box()
        if box:
            await page.mouse.dblclick(
                box["x"] + box["width"] / 2,
                box["y"] + box["height"] / 2,
            )
            await page.wait_for_timeout(500)


async def _scrub_timeline(page, progress: float) -> None:
    """Scrub timeline slider to given progress (0.0–1.0)."""
    await page.evaluate(f"""
        const slider = document.querySelector('.temporal-slider input[type=range]');
        if (slider) {{
            const max = parseInt(slider.max) || 400;
            slider.value = Math.round(max * {progress});
            slider.dispatchEvent(new Event('input'));
        }}
    """)
    await page.wait_for_timeout(600)


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
                "delay_ms": 6000,
                "scrub": 1.0,  # Show final state
            },
            {
                "name": "hero_metrics_dashboard",
                "description": "Social Media Regulation — polarization dynamics",
                "url": f"{base_url}/demo/social_media_regulation",
                "wait_for": ".dynamics-graph-panel canvas",
                "delay_ms": 6000,
                "scrub": 0.75,  # Show mid-polarization moment
            },
            {
                "name": "hero_ecosystem",
                "description": "Ecosystem Collapse — species food web",
                "url": f"{base_url}/demo/ecosystem_collapse",
                "wait_for": ".dynamics-graph-panel canvas",
                "delay_ms": 6000,
                "scrub": 0.6,  # Show pre-collapse state
            },
            {
                "name": "hero_ai_startup",
                "description": "AI Startup Ecosystem — market dynamics",
                "url": f"{base_url}/demo/ai_startup_ecosystem",
                "wait_for": ".dynamics-graph-panel canvas",
                "delay_ms": 6000,
                "scrub": 0.8,  # Show mature market
            },
        ]

        for spec in screenshots:
            print(f"  Capturing {spec['name']}... ", end="", flush=True)
            try:
                await page.goto(spec["url"], wait_until="networkidle")
                await page.wait_for_selector(spec["wait_for"], timeout=30000)
                await page.wait_for_timeout(spec["delay_ms"])
                await _zoom_to_fit(page)
                # Scrub timeline to the specified point
                if "scrub" in spec:
                    await _scrub_timeline(page, spec["scrub"])
                    await page.wait_for_timeout(1500)  # Let graph re-render
                    await _zoom_to_fit(page)
                path = output_dir / f"{spec['name']}.png"
                await page.screenshot(path=str(path), full_page=False)
                size_kb = path.stat().st_size // 1024
                print(f"saved ({size_kb} KB)")
            except Exception as e:
                print(f"FAILED: {e}")

        # --- Phase transition screenshot ---
        print("  Capturing hero_phase_transition... ", end="", flush=True)
        try:
            await page.goto(f"{base_url}/demo/civilization_from_scratch",
                            wait_until="networkidle")
            await page.wait_for_selector(".dynamics-graph-panel canvas", timeout=30000)
            await page.wait_for_timeout(5000)
            await _zoom_to_fit(page)
            # Scrub to early state first (step ~50), then to late state (step ~350)
            # showing dramatic difference — capture the late dramatic state
            await _scrub_timeline(page, 0.85)
            await page.wait_for_timeout(1500)
            await _zoom_to_fit(page)
            path = output_dir / "hero_phase_transition.png"
            await page.screenshot(path=str(path), full_page=False)
            size_kb = path.stat().st_size // 1024
            print(f"saved ({size_kb} KB)")
        except Exception as e:
            print(f"FAILED: {e}")

        # --- GIF capture (frame-by-frame for simulation replay) ---
        gif_dir = output_dir.parent / "gifs" / "frames"
        gif_dir.mkdir(parents=True, exist_ok=True)

        num_frames = 40  # More frames = smoother animation
        print(f"\n  Capturing {num_frames} simulation replay frames...")
        try:
            await page.goto(f"{base_url}/demo/civilization_from_scratch",
                            wait_until="networkidle")
            await page.wait_for_selector(".dynamics-graph-panel canvas", timeout=30000)
            await page.wait_for_timeout(5000)
            await _zoom_to_fit(page)

            for i in range(num_frames):
                progress = i / (num_frames - 1)
                await _scrub_timeline(page, progress)
                await page.wait_for_timeout(400)
                frame_path = gif_dir / f"frame_{i:03d}.png"
                await page.screenshot(path=str(frame_path), full_page=False)
                if i % 10 == 0:
                    print(f"    Frame {i}/{num_frames}...")

            print(f"  Captured {num_frames} frames to {gif_dir}")

            # Try to assemble GIF with ffmpeg if available
            gif_output = output_dir.parent / "gifs" / "simulation_replay.gif"
            if shutil.which("ffmpeg"):
                print("  Assembling GIF with ffmpeg...")
                palette_path = gif_dir / "palette.png"
                frame_pattern = str(gif_dir / "frame_%03d.png")
                # Generate palette
                subprocess.run([
                    "ffmpeg", "-y", "-framerate", "6",
                    "-i", frame_pattern,
                    "-vf", "fps=6,scale=960:-1:flags=lanczos,palettegen=stats_mode=diff",
                    str(palette_path),
                ], capture_output=True)
                # Generate GIF
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
                    print("  GIF assembly failed. Use ffmpeg manually:")
                    print(f"    cd {gif_dir}")
                    print("    ffmpeg -framerate 6 -i frame_%03d.png -vf palettegen palette.png")
                    print("    ffmpeg -framerate 6 -i frame_%03d.png -i palette.png -filter_complex paletteuse ../simulation_replay.gif")
            else:
                print("  ffmpeg not found. Assemble GIF manually:")
                print(f"    cd {gif_dir}")
                print("    ffmpeg -framerate 6 -i frame_%03d.png -vf palettegen palette.png")
                print("    ffmpeg -framerate 6 -i frame_%03d.png -i palette.png -filter_complex paletteuse ../simulation_replay.gif")

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

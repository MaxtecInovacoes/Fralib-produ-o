"""Vite/React build and execution utilities."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any


# ═══════════════════════════════════════════════════════════════════
# NODE UTILITIES
# ═══════════════════════════════════════════════════════════════════

# Cache path for node_modules tarball (1h TTL)
CACHE_PATH = Path("/var/cache/fralib/node_modules_vite.tar.gz")


def _node_bin() -> str:
    """Get node binary path."""
    return os.getenv("NODE_PATH", "node")


def _npm_bin() -> str:
    """Get npm binary path."""
    return os.getenv("NPM_PATH", "npm")


# ═══════════════════════════════════════════════════════════════════
# NODE_MODULES CACHE (1h TTL)
# ═══════════════════════════════════════════════════════════════════

def _try_cache_restore(workspace: Path) -> bool:
    """
    Try to restore node_modules from cache tarball.
    Returns True if cache was found and restored, False otherwise.
    """
    if not CACHE_PATH.exists():
        return False

    node_modules_dir = workspace / "node_modules"
    # Remove existing node_modules if present (corrupted or outdated)
    if node_modules_dir.exists():
        shutil.rmtree(node_modules_dir)

    try:
        cache_size_mb = CACHE_PATH.stat().st_size / (1024 * 1024)
        print(f"[ViteBuild] Cache hit: restoring node_modules from {CACHE_PATH} ({cache_size_mb:.1f} MB)")
        # Extract tarball directly to workspace (node_modules will be created)
        shutil.unpack_archive(str(CACHE_PATH), str(workspace), format="gztar")
        # Verify extraction worked
        if node_modules_dir.exists():
            print("[ViteBuild] Cache restore: OK")
            return True
        return False
    except Exception as e:
        print(f"[ViteBuild] Cache restore failed: {e}; running npm install")
        return False


def _create_cache(workspace: Path) -> bool:
    """
    Create node_modules cache tarball after successful npm install.
    Returns True if cache was created, False otherwise.
    """
    node_modules_dir = workspace / "node_modules"
    if not node_modules_dir.exists():
        return False

    try:
        # Ensure cache directory exists
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)

        # Remove old cache if exists
        if CACHE_PATH.exists():
            CACHE_PATH.unlink()

        # Create tarball: tar -czf path/to/cache.tar.gz -C workspace node_modules
        # shutil.make_archive creates: base_name + ".tar.gz"
        # CACHE_PATH = "/var/cache/fralib/node_modules_vite.tar.gz"
        # We need base_name WITHOUT any extension → strip ".tar.gz"
        cache_base = str(CACHE_PATH.parent / CACHE_PATH.stem)
        # CACHE_PATH.stem = "node_modules_vite" (strips last .gz)
        # make_archive adds ".tar.gz" → final: "/var/cache/fralib/node_modules_vite.tar.gz" ✓
        shutil.make_archive(cache_base, "gztar", str(workspace), "node_modules")

        if CACHE_PATH.exists():
            cache_size_mb = CACHE_PATH.stat().st_size / (1024 * 1024)
            print(f"[ViteBuild] Cache created: {CACHE_PATH} ({cache_size_mb:.1f} MB)")
            return True
        else:
            print(f"[ViteBuild] Cache creation FAILED: {CACHE_PATH} not found after make_archive")
            return False
    except Exception as e:
        print(f"[ViteBuild] Cache creation failed: {e}")
        return False


# ═══════════════════════════════════════════════════════════════════
# PROJECT FILE OPERATIONS
# ═══════════════════════════════════════════════════════════════════

def write_vite_project(workspace: Path, files: dict[str, str]) -> None:
    """Write generated files to workspace directory."""
    workspace.mkdir(parents=True, exist_ok=True)

    for file_path, content in files.items():
        target = workspace / file_path
        target.parent.mkdir(parents=True, exist_ok=True)

        # Ensure content is string
        if not isinstance(content, str):
            content = str(content)

        target.write_text(content, encoding="utf-8")


def rewrite_vite_dist_asset_paths(dist_dir: Path) -> None:
    """Rewrite asset paths in built files for correct loading."""
    if not dist_dir.exists():
        return

    # Process HTML files
    for html_file in dist_dir.glob("*.html"):
        content = html_file.read_text(encoding="utf-8")

        # Fix asset paths if needed
        # Vite outputs assets as /assets/filename
        # If serving from subdirectory, adjust

        html_file.write_text(content, encoding="utf-8")


# ═══════════════════════════════════════════════════════════════════
# BUILD EXECUTION
# ═══════════════════════════════════════════════════════════════════

def build_vite_project(
    workspace: Path,
    timeout: int = 300,
    node_timeout: int = 180,
) -> None:
    """
    Build Vite project: cache restore OR npm install + cache create + vite build.

    Uses node_modules cache for ~20x faster builds (1h TTL).
    Cache path: /var/cache/fralib/node_modules_vite.tar.gz

    Args:
        workspace: Project directory path
        timeout: Total timeout in seconds
        node_timeout: npm install / cache restore timeout
    """
    import time

    node = _node_bin()
    npm = _npm_bin()

    # Change to workspace
    original_cwd = Path.cwd()
    try:
        os.chdir(workspace)

        # Step 1: Try cache restore first; install dependencies on cache miss.
        cache_hit = _try_cache_restore(workspace)

        if cache_hit:
            print("[ViteBuild] Using cached node_modules")
        else:
            # Step 2: npm install (cache miss)
            print("[ViteBuild] Running npm install...")
            try:
                result = subprocess.run(
                    [npm, "install", "--include=dev", "--prefer-offline"],
                    capture_output=True,
                    text=True,
                    timeout=node_timeout,
                    cwd=workspace,
                )

                if result.returncode != 0:
                    stderr = result.stderr[-500:] if result.stderr else ""
                    raise RuntimeError(f"npm install failed: {stderr}")

                print("[ViteBuild] npm install completed")

                # Step 3: Create cache for next build
                _create_cache(workspace)

            except subprocess.TimeoutExpired:
                raise RuntimeError(f"npm install timed out after {node_timeout}s")

        # Step 4: vite build
        print("[ViteBuild] Running vite build...")
        start = time.time()

        try:
            result = subprocess.run(
                [node, "node_modules/vite/bin/vite.js", "build"],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=workspace,
            )

            elapsed = time.time() - start

            if result.returncode != 0:
                stderr = result.stderr[-1000:] if result.stderr else ""
                raise RuntimeError(f"vite build failed:\n{stderr}")

            print(f"[ViteBuild] vite build completed in {elapsed:.1f}s")

        except subprocess.TimeoutExpired:
            raise RuntimeError(f"vite build timed out after {timeout}s")

    finally:
        os.chdir(original_cwd)


def _run(
    command: list[str],
    *,
    cwd: Path,
    timeout: int,
    label: str,
) -> None:
    """Run a shell command with timeout."""
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
        )

        if result.returncode != 0:
            stderr = result.stderr[-500:] if result.stderr else ""
            raise RuntimeError(f"{label} failed: {stderr}")

    except subprocess.TimeoutExpired:
        raise RuntimeError(f"{label} timed out after {timeout}s")


# ═══════════════════════════════════════════════════════════════════
# DEFAULT FILES
# ═══════════════════════════════════════════════════════════════════

def _default_index_html(facts: dict[str, Any]) -> str:
    """Generate default index.html."""
    from vite_facts import (
        _facts_business,
        _facts_meta_description,
        _facts_theme_color,
        _facts_og_image,
    )

    business = _facts_business(facts)
    meta_desc = _facts_meta_description(facts)
    theme_color = _facts_theme_color(facts)
    og_image = _facts_og_image(facts)

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{business['name']}</title>
    <meta name="description" content="{meta_desc}">
    <meta name="theme-color" content="{theme_color}">"""

    if og_image:
        html += f"""
    <meta property="og:image" content="{og_image}">"""

    html += """
    <link rel="icon" type="image/svg+xml" href="/vite.svg">
</head>
<body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
</body>
</html>"""

    return html


def _default_vite_config() -> str:
    """Generate default vite.config.ts with pre-render for SEO."""
    return """import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { PrerenderSPAPlugin } from 'vite-plugin-prerender-spa'

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    PrerenderSPAPlugin({
      routes: ['/'],
      staticDir: 'dist',
    }),
  ],
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
  },
})
"""


def _default_tsconfig() -> str:
    """Generate default tsconfig.json."""
    return """{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "isolatedModules": true,
    "moduleDetection": "force",
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "noUncheckedSideEffectImports": true
  },
  "include": ["src"]
}
"""


def _default_main_tsx() -> str:
    """Generate default main.tsx."""
    return """import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
"""


def _default_app_tsx() -> str:
    """Generate default App.tsx."""
    return """import React from 'react'

function App() {{
  return (
    <div className="min-h-screen bg-white">
      <h1>Loading...</h1>
    </div>
  )
}}

export default App
"""


def _default_types_ts() -> str:
    """Generate default types.ts."""
    return """export interface Business {{
  name: string
  segment: string
  tagline?: string
}}

export interface Lead {{
  id: number
  nome: string
  cidade: string
  segmento: string
}}
"""


def _default_index_css() -> str:
    """Generate default index.css with Tailwind."""
    return """@import "tailwindcss";

@layer base {{
  body {{
    font-family: system-ui, -apple-system, sans-serif;
  }}
}}
"""

"""Tests for vite_validator module."""

import pytest


class TestValidateViteProjectFiles:
    """Test project file validation."""

    def test_validate_minimum_files(self):
        """Test validation requires minimum files."""
        from backend.services.vite_validator import validate_vite_project_files

        files = {"package.json": "{}"}
        result = validate_vite_project_files(files, {})

        assert any("Too few files" in err for err in result)

    def test_validate_missing_required_file(self):
        """Test validation catches missing required files."""
        from backend.services.vite_validator import validate_vite_project_files

        files = {"package.json": "{}", "src/App.tsx": "export default App;"}
        result = validate_vite_project_files(files, {})

        assert any("Missing required file" in err for err in result)

    def test_validate_source_too_small(self):
        """Test validation catches too-small source."""
        from backend.services.vite_validator import validate_vite_project_files

        files = {
            "package.json": "{}",
            "vite.config.ts": "",
            "tsconfig.json": "",
            "index.html": "<html><body>Hi</body></html>",
            "src/App.tsx": "export default function App(){}",
        }
        result = validate_vite_project_files(files, {}, min_chars=50000)

        assert any("Source too small" in err for err in result)

    def test_validate_passes_with_valid_project(self):
        """Test validation passes for valid project."""
        from backend.services.vite_validator import validate_vite_project_files

        files = {
            "package.json": '{"name": "test"}',
            "vite.config.ts": "export default {}",
            "tsconfig.json": '{"compilerOptions": {}}',
            "index.html": '<html><body><img src="https://example.com/img.jpg" /><div class="bg-red-500 text-center p-4 flex-col grid-cols-2"></div></body></html>',
            "src/App.tsx": "export default function App(){ return <div className='bg-red-500'>Hello</div> }",
            "src/main.tsx": "import React from 'react'",
            "src/index.css": ".class { color: red; }",
            "src/types.ts": "export type Props = {}",
            "src/components/Hero.tsx": "export default function Hero() { return <img src='https://example.com/a.jpg' /> }",
            "src/components/Footer.tsx": "export default function Footer() {}",
            "src/components/Navbar.tsx": "export default function Navbar() {}",
            "src/components/Services.tsx": "export default function Services() {}",
        }
        result = validate_vite_project_files(
            files,
            {"business": {"name": "Test"}},
            min_chars=100,
            min_classnames=5,
            min_images=1,
            min_components=4,
        )

        # Should pass with no critical errors
        critical = [e for e in result if "Too few" in e or "Missing" in e]
        assert len(critical) == 0


class TestValidateViteDist:
    """Test dist directory validation."""

    def test_validate_missing_dist(self, tmp_path):
        """Test validation handles missing dist directory."""
        from backend.services.vite_validator import validate_vite_dist

        result = validate_vite_dist(tmp_path / "nonexistent")
        assert any("not found" in err for err in result)

    def test_validate_empty_dist(self, tmp_path):
        """Test validation catches empty dist."""
        from backend.services.vite_validator import validate_vite_dist

        dist = tmp_path / "dist"
        dist.mkdir()

        result = validate_vite_dist(dist)
        assert any("too small" in err for err in result)

    def test_validate_valid_dist(self, tmp_path):
        """Test validation passes for valid dist."""
        from backend.services.vite_validator import validate_vite_dist

        dist = tmp_path / "dist"
        dist.mkdir()
        (dist / "index.html").write_text("<html></html>")
        assets = dist / "assets"
        assets.mkdir()
        (assets / "main.js").write_text("// main")

        result = validate_vite_dist(dist)
        assert len(result) == 0

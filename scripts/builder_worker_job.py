"""Create or execute an isolated prompt-to-app builder manifest."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from services.builder_worker import (  # noqa: E402
    build_builder_job_manifest,
    render_site_with_builder,
    write_builder_job_manifest,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prd-json", required=True)
    parser.add_argument("--tenant-id", required=True)
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--target", default="landing-page")
    parser.add_argument("--model", default="sonnet", help="OpenUI primary model alias")
    parser.add_argument("--manifest-dir", default=str(ROOT / ".tmp" / "builder-jobs"))
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    prd = json.loads(Path(args.prd_json).read_text(encoding="utf-8"))
    manifest = build_builder_job_manifest(
        prd,
        tenant_id=args.tenant_id,
        job_id=args.job_id,
        target=args.target,
        agent="openui",
        model=args.model,
        sandbox_root=os.getenv(
            "FRALIB_BUILDER_SANDBOX_ROOT",
            str((ROOT / ".tmp" / "builder-workspaces").resolve()).replace("\\", "/"),
        ),
    )
    path = write_builder_job_manifest(manifest, manifest_dir=args.manifest_dir)
    print(
        json.dumps(
            {
                "ok": True,
                "mode": manifest["mode"],
                "tenant_id": manifest["tenant_id"],
                "job_id": manifest["job_id"],
                "workspace": manifest["sandbox"]["workspace"],
                "manifest": str(path),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    if args.execute:
        os.environ.setdefault("FRALIB_OPENUI_PRIMARY_MODEL", args.model)
        try:
            from agents.llm_direct import set_current_user_id

            set_current_user_id(args.tenant_id)
        except Exception:
            pass
        result = render_site_with_builder(
            prd,
            tenant_id=args.tenant_id,
            job_id=args.job_id,
            target=args.target,
        )
        print(
            json.dumps(
                {
                    "ok": True,
                    "engine": result.get("engine"),
                    "model": result.get("model"),
                    "index_path": result.get("index_path"),
                    "output_dir": result.get("output_dir"),
                    "manifest": result.get("manifest_path"),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

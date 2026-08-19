import re
path = r"C:\fralib\backend\agents\builder\agent.py"
with open(path, encoding='utf-8') as f:
    src = f.read()
old = r'''    # Animations / motion directives
    animations = getattr(prd, "animations", None) or []
    if isinstance(animations, str):
        try:
            import json
            animations = json.loads(animations)
        except Exception:
            animations = []

    motion_directives = {
        "aos": True,
        "duration": "700ms",
        "once": True,
        "offset": 40,
        "animations": [
            {
                "name": getattr(a, "name", a.get("name", "fade-up")) if hasattr(a, "name") else a.get("name", "fade-up"),
                "type": getattr(a, "type", a.get("type", "fade-up")) if hasattr(a, "type") else a.get("type", "fade-up"),
                "duration": getattr(a, "duration", a.get("duration", "700ms")) if hasattr(a, "duration") else a.get("duration", "700ms"),
            }
            for a in animations[:5]
        ],
    }'''
new = r'''    # Animations / motion directives
    animations = getattr(prd, "animations", None) or []
    if isinstance(animations, str):
        try:
            import json
            animations = json.loads(animations)
        except Exception:
            animations = []

    # Normalize Pydantic AnimationSpec -> dict so downstream .get() works
    _anim_out = []
    for _a in animations[:5]:
        if isinstance(_a, dict):
            _anim_out.append(_a)
        else:
            _anim_out.append({_k: getattr(_a, _k, _v) for _k, _v in {"name": "fade-up", "type": "fade-up", "duration": "700ms"}.items()})
    animations = _anim_out

    motion_directives = {
        "aos": True,
        "duration": "700ms",
        "once": True,
        "offset": 40,
        "animations": [
            {
                "name": a.get("name", "fade-up"),
                "type": a.get("type", "fade-up"),
                "duration": a.get("duration", "700ms"),
            }
            for a in animations
        ],
    }'''
if old not in src:
    print("OLD BLOCK NOT FOUND — scanning for partial match")
    for i in range(10):
        snippet = src[i*100:(i+1)*100]
        if "Animations / motion directives" in snippet:
            print("Found at offset", i*100)
            break
    raise SystemExit(1)
src = src.replace(old, new, 1)
with open(path, "w", encoding="utf-8") as f:
    f.write(src)
print("PATCHED local builder")

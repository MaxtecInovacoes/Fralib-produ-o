import json, subprocess
result = subprocess.run(["pm2", "jlist"], capture_output=True, text=True)
data = json.loads(result.stdout)
for p in data:
    name = p["name"]
    pid = p["pid"]
    env = p["pm2_env"]
    script = env.get("pm_exec_path", "?")
    args = env.get("args", [])
    cwd = env.get("pm_cwd", "?")
    print(f"{name:25} pid={pid:7} script={script}")
    print(f"  args={args}")
    print(f"  cwd={cwd}")
    print()
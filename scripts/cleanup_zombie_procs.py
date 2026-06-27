"""Cron job pra limpar processos duplicados do Franz.

Roda a cada 5 min. Detecta e mata processos Python zumbis que nao estao
gerenciados pelo PM2 (causa raiz do bug 3x que sempre voltava).

Logs: /var/log/fralib-cleanup.log
"""

import os
import subprocess
import re

def cleanup_zombies():
    """Encontra e mata processos duplicados nao-gerenciados pelo PM2."""
    try:
        # Listar todos os processos Python do fralib
        result = subprocess.run(
            ["ps", "-eo", "pid,etime,cmd"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            return

        # Pegar PIDs gerenciados pelo PM2
        pm2_result = subprocess.run(
            ["pm2", "list", "--no-color"],
            capture_output=True, text=True, timeout=10
        )

        managed_pids = set()
        for line in pm2_result.stdout.split("\n"):
            # Linhas com pid estao no formato "│ pid │ ..."
            m = re.search(r"│\s*(\d+)\s*│", line)
            if m:
                managed_pids.add(int(m.group(1)))

        # Contar worker.py / server.py / listener rodando
        worker_procs = []
        server_procs = []
        listener_procs = []

        for line in result.stdout.split("\n"):
            if "fralib" in line and "python" in line:
                m = re.match(r"\s*(\d+)\s+(\d+):?(\d+)?:?(\d+)?\s+.*?(fralib.*worker\.py|fralib.*server\.py|fralib.*whatsapp_listener\.py)", line)
                if not m:
                    continue
                pid = int(m.group(1))
                uptime_sec = int(m.group(2)) if m.group(2) else 0
                script = m.group(6) if len(m.groups()) >= 6 else ""

                if pid in managed_pids:
                    continue  # PM2 ta gerenciando, nao mexer

                # Nao gerenciado pelo PM2 = zumbi
                if "worker.py" in script:
                    worker_procs.append((pid, uptime_sec))
                elif "server.py" in script:
                    server_procs.append((pid, uptime_sec))
                elif "whatsapp_listener" in script:
                    listener_procs.append((pid, uptime_sec))

        # Matar duplicados (mantem o mais antigo)
        all_dups = worker_procs + server_procs + listener_procs
        if len(all_dups) > 3:  # max 1 de cada
            # Ordenar por uptime (mais antigo primeiro = manter)
            all_dups.sort(key=lambda x: -x[1])
            # Manter 1 worker, 1 server, 1 listener (os mais antigos)
            to_kill = all_dups[3:]  # mata do 4º em diante
            for pid, uptime in to_kill:
                print(f"Killing zombie PID {pid} (uptime {uptime}s)")
                try:
                    os.kill(pid, 9)
                except ProcessLookupError:
                    pass

        # Verificar se ha processos NAO-gerenciados pelo PM2 de listener
        if listener_procs and all(pid not in managed_pids for pid, _ in listener_procs):
            print(f"WARNING: listener processes nao gerenciados pelo PM2: {listener_procs}")
    except Exception as e:
        print(f"ERROR in cleanup: {e}")


if __name__ == "__main__":
    cleanup_zombies()
    # PM2 nao sabe de processos nao-gerenciados por ele
    # Roda em background infinito
    import time
    while True:
        time.sleep(300)  # 5 min
        cleanup_zombies()
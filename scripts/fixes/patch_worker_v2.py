with open("/opt/fralib/worker.py") as f:
    src = f.read()

old = '''            if job["tipo"] == "pipeline_lead":
                return _run_pipeline_job(db, job)
            return _run_supply_job(db, job)'''

new = '''            if job["tipo"] == "pipeline_lead":
                try:
                    return _run_pipeline_job(db, job)
                except Exception as exc:
                    logger.exception("Job %s (pipeline_lead) CRASHED: %s", job["id"], exc)
                    try:
                        job_queue.mark_failure(db, job["id"], error=str(exc)[:1000], retriable=True)
                    except Exception:
                        pass
                    return True
            return _run_supply_job(db, job)'''

if old in src:
    src = src.replace(old, new)
    with open("/opt/fralib/worker.py", "w") as f:
        f.write(src)
    print("OK: patched run_one() pipeline_lead call")
else:
    print("ERROR: pattern not found")
    idx = src.find("pipeline_lead")
    print(src[max(0,idx-50):idx+200])

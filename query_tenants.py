# -*- coding: utf-8 -*-
import psycopg2
import json
import sys

def main():
    # Force UTF-8 encoding for all streams
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

    # Try connection
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        database="fralib_db",
        user="postgres",
        password="fralib2024"
    )
    print("Connected successfully!", flush=True)

    cur = conn.cursor()

    # Get tenants
    cur.execute("SELECT id, email, plano, nicho FROM users ORDER BY id")
    rows = cur.fetchall()
    print(f"\nFound {len(rows)} tenants", flush=True)

    # Store results for structured output
    all_tenants = []

    for row in rows:
        tenant_id, email, plano, nicho = row
        tenant_data = {
            'id': tenant_id,
            'email': email,
            'plano': plano,
            'nicho': nicho,
            'sdr_settings': None,
            'pipeline_state': None,
            'lead_supply_config': None,
            'lead_counts': {}
        }

        # SDR settings
        cur.execute("""
            SELECT config FROM user_configs
            WHERE user_id = %s AND key = 'sdr_settings_v1'
        """, (tenant_id,))
        sdr_row = cur.fetchone()

        if sdr_row:
            config = sdr_row[0]
            if isinstance(config, str):
                try:
                    config = json.loads(config)
                except:
                    pass
            tenant_data['sdr_settings'] = config

        # Pipeline state
        cur.execute("""
            SELECT config FROM user_configs
            WHERE user_id = %s AND key = 'pipeline_state'
        """, (tenant_id,))
        pipeline_row = cur.fetchone()

        if pipeline_row:
            config = pipeline_row[0]
            if isinstance(config, str):
                try:
                    config = json.loads(config)
                except:
                    pass
            tenant_data['pipeline_state'] = config

        # Lead supply config
        cur.execute("""
            SELECT config FROM user_configs
            WHERE user_id = %s AND key = 'lead_supply_config'
        """, (tenant_id,))
        lsc_row = cur.fetchone()

        if lsc_row:
            config = lsc_row[0]
            if isinstance(config, str):
                try:
                    config = json.loads(config)
                except:
                    pass
            tenant_data['lead_supply_config'] = config

        # Lead counts
        cur.execute("""
            SELECT status, COUNT(*) as count
            FROM leads
            WHERE user_id = %s
            GROUP BY status
        """, (tenant_id,))
        lead_counts = cur.fetchall()
        for status, count in lead_counts:
            tenant_data['lead_counts'][status] = count

        all_tenants.append(tenant_data)

    # Output JSON for structured processing
    print("\n=== STRUCTURED DATA ===", flush=True)
    print(json.dumps(all_tenants, ensure_ascii=False, indent=2, default=str), flush=True)

    conn.close()

if __name__ == "__main__":
    main()

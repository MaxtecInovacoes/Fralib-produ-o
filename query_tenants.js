const { Client } = require('pg');

async function main() {
    const client = new Client({
        host: 'localhost',
        port: 5432,
        database: 'fralib_db',
        user: 'postgres',
        password: 'fralib2024'
    });

    try {
        await client.connect();
        console.log('Connected to PostgreSQL!');

        // Get tenants
        const usersResult = await client.query('SELECT id, email, plano, nicho FROM users ORDER BY id');
        const users = usersResult.rows;
        console.log(`\nFound ${users.length} tenants\n`);

        for (const user of users) {
            console.log('='.repeat(80));
            console.log(`TENANT: ${user.email}`);
            console.log(`  ID: ${user.id} | Plano: ${user.plano} | Nicho: ${user.nicho}`);
            console.log('');

            // SDR settings
            const sdrResult = await client.query(
                'SELECT config_value FROM user_configs WHERE user_id = $1 AND config_key = $2',
                [user.id, 'sdr_settings_v1']
            );

            if (sdrResult.rows.length > 0) {
                const sdr = JSON.parse(sdrResult.rows[0].config_value);
                console.log('  SDR_SETTINGS_V1:');
                console.log(`    agent_name: ${sdr.agent_name || 'N/A'}`);
                console.log(`    limits: ${JSON.stringify(sdr.limits || {})}`);
                console.log(`    schedule: ${JSON.stringify(sdr.outbound_schedule || {})}`);
                console.log(`    blocked_actions: ${JSON.stringify(sdr.blocked_actions || [])}`);
                console.log(`    allowed_actions: ${JSON.stringify(sdr.allowed_actions || [])}`);
                console.log(`    handoff: ${JSON.stringify(sdr.handoff || {})}`);
            } else {
                console.log('  SDR_SETTINGS_V1: NOT CONFIGURED');
            }
            console.log('');

            // Pipeline state
            const pipeResult = await client.query(
                'SELECT config_value FROM user_configs WHERE user_id = $1 AND config_key = $2',
                [user.id, 'pipeline_state']
            );

            if (pipeResult.rows.length > 0) {
                console.log('  PIPELINE_STATE:');
                const pipeline = JSON.parse(pipeResult.rows[0].config_value);
                console.log(`    ${JSON.stringify(pipeline)}`);
            } else {
                console.log('  PIPELINE_STATE: NOT CONFIGURED');
            }
            console.log('');

            // Lead supply config
            const lscResult = await client.query(
                'SELECT config_value FROM user_configs WHERE user_id = $1 AND config_key = $2',
                [user.id, 'lead_supply_config']
            );

            if (lscResult.rows.length > 0) {
                console.log('  LEAD_SUPPLY_CONFIG:');
                const lsc = JSON.parse(lscResult.rows[0].config_value);
                console.log(`    ${JSON.stringify(lsc, null, 4)}`);
            } else {
                console.log('  LEAD_SUPPLY_CONFIG: NOT CONFIGURED');
            }
            console.log('');

            // Lead counts
            const leadResult = await client.query(
                'SELECT status, COUNT(*) as count FROM leads WHERE user_id = $1 GROUP BY status',
                [user.id]
            );

            console.log('  LEAD STATUS COUNTS:');
            let pendingSdr = 0;
            let pendingWpp = 0;
            for (const row of leadResult.rows) {
                console.log(`    ${row.status}: ${row.count}`);
                if (row.status === 'pending_sdr_send') pendingSdr = parseInt(row.count);
                if (row.status === 'pendente_wpp') pendingWpp = parseInt(row.count);
            }
            console.log(`  -> Leads stuck at pending_sdr_send: ${pendingSdr}`);
            console.log(`  -> Leads stuck at pendente_wpp: ${pendingWpp}`);
            console.log('');
        }

        await client.end();
    } catch (err) {
        console.error('Error:', err);
        process.exit(1);
    }
}

main();

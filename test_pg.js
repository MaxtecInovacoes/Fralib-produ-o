const { Client } = require('pg');

async function main() {
    // Try different connection variations
    const configs = [
        {
            host: 'localhost',
            port: 5432,
            database: 'fralib_db',
            user: 'postgres',
            password: 'fralib2024'
        },
        {
            connectionString: 'postgresql://postgres:fralib2024@localhost:5432/fralib_db'
        }
    ];

    for (const config of configs) {
        const client = new Client(config);
        try {
            await client.connect();
            console.log('Connected with config:', JSON.stringify(config).replace(/password/g, '***'));

            // Test query
            const result = await client.query('SELECT 1 as test');
            console.log('Test query result:', result.rows);

            await client.end();
            break;
        } catch (err) {
            console.log('Failed with config:', JSON.stringify(config).replace(/password/g, '***'));
            console.log('Error:', err.message);
        }
    }
}

main();

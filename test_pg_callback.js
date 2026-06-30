const { Client } = require('pg');

// Try with password callback
const client = new Client({
    host: 'localhost',
    port: 5432,
    database: 'fralib_db',
    user: 'postgres',
    password: (text) => {
        console.log('Password callback invoked with:', text);
        return 'fralib2024';
    }
});

client.connect()
    .then(() => { console.log('Connected!'); client.end(); })
    .catch(e => { console.log('Error:', e.message); });

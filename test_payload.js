const http = require('http');

const server = http.createServer((req, res) => {
    let body = '';
    req.on('data', chunk => body += chunk);
    req.on('end', () => {
        console.log('--- PAYLOAD ---');
        console.log(JSON.stringify(JSON.parse(body), null, 2));
        res.writeHead(200);
        res.end();
        server.close();
        process.exit(0);
    });
});

server.listen(4097, async () => {
    const { OpencodeClient } = await import('@opencode-ai/sdk');
    const client = new OpencodeClient({ baseURL: 'http://127.0.0.1:4097', token: 'fake' });
    try {
        await client.session.prompt({
            sessionID: 'ses_14397b860ffep4XABuc8yAFpvQ',
            prompt: 'hi'
        });
    } catch (e) { console.error('ERROR', e); process.exit(1); }
});

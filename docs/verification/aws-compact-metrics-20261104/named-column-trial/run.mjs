import { mkdtemp, mkdir, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { createServer } from 'node:net';
import { spawn } from 'node:child_process';
const folder = dirname(fileURLToPath(import.meta.url));
const phase = process.argv[2] || 'after';
if (!/^[a-z0-9-]+$/.test(phase)) throw Error('Invalid phase');
const out = join(folder, phase);
await mkdir(out, { recursive: true });
const { default: PG } = await import(pathToFileURL(join(process.env.STATARENA_TEST_TOOLS || '/tmp/statarena-cache-test-tools', 'node_modules/embedded-postgres/dist/index.js')));
const socket = createServer();
await new Promise(r => socket.listen(0, '127.0.0.1', r));
const port = socket.address().port;
await new Promise(r => socket.close(r));
const scratch = await mkdtemp(join(tmpdir(), 'relational-publisher-pg-'));
const logs = [], pg = new PG({ databaseDir: join(scratch, 'data'), user:'fixture', password:'local-only', port, persistent:false, postgresFlags:['-c','listen_addresses=127.0.0.1'], onLog:s=>logs.push(String(s)),onError:s=>logs.push(String(s)) });
try {
  await pg.initialise(); await pg.start(); const legacy=phase==='legacy-regression';
  const database = legacy ? 'archive_materialization_e2e' : 'publication_fixture';
  await pg.createDatabase(database);
  const child = spawn('python3', legacy ? ['tests/rematerialize_archive_postgres.py','--report',join(out,'results.json')] : [join(folder,'verify.py'), phase], {cwd:folder,stdio:['ignore','pipe','pipe'],env:{
    PATH:process.env.PATH, HOME:scratch, PYTHONDONTWRITEBYTECODE:'1',
    PYTHONPATH:process.env.STATARENA_TEST_PYTHON || '/tmp/statarena-publication-test-python',
    TEST_DATABASE_URL:`postgresql://fixture:local-only@127.0.0.1:${port}/${database}`,
  }});
  let logs = '';
  for (const stream of [child.stdout,child.stderr]) stream.on('data',chunk=>{logs+=chunk;process.stdout.write(chunk)});
  process.exitCode = await new Promise((r,j)=>{child.once('error',j);child.once('close',r)});
  await writeFile(join(out,'worker.log'),logs);
} finally {
  await pg.stop(); await rm(scratch,{recursive:true,force:true});
  await writeFile(join(out,'postgres.log'),logs.join('\n'));
}

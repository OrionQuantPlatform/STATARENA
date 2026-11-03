import EmbeddedPostgres from '/tmp/statarena-archive-remat-pg/node_modules/embedded-postgres/dist/index.js';
import {mkdtempSync,appendFileSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join,resolve} from 'node:path';
import {createServer} from 'node:net';
import {spawn} from 'node:child_process';
const phase=process.argv[2]||'after',out=resolve('output/playwright/rematerialization-completion-20261103');
const server=createServer();await new Promise(r=>server.listen(0,'127.0.0.1',r));const port=server.address().port;await new Promise(r=>server.close(r));
const root=mkdtempSync(join(tmpdir(),'statarena-archive-postgres-'));
const pg=new EmbeddedPostgres({databaseDir:join(root,'data'),user:'postgres',password:'local-e2e-only',port,persistent:false,onLog:s=>appendFileSync(join(out,phase+'-postgres.log'),String(s)+'\n'),onError:s=>appendFileSync(join(out,phase+'-postgres.log'),String(s)+'\n')});
let code=1;
try {await pg.initialise();await pg.start();await pg.createDatabase('archive_materialization_e2e');
 const args=phase==='daily'?['tests/daily_refresh_postgres.py']:['tests/rematerialize_archive_postgres.py','--report',join(out,phase+'-archive-postgres.json')];
 const child=spawn('python3',args,{env:{...process.env,TEST_DATABASE_URL:`postgresql://postgres:local-e2e-only@127.0.0.1:${port}/archive_materialization_e2e`,PYTHONPATH:'/tmp/statarena-archive-remat-pg/python'},stdio:'inherit'});
 code=await new Promise(r=>child.on('exit',r));
} finally {await pg.stop();}
process.exitCode=code;

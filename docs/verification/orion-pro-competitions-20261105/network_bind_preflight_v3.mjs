import net from "node:net";
import dns from "node:dns";
import http from "node:http";
import https from "node:https";
const pgPort=35555;
const attempts = [], calibration = [];
let calibrating = true;
function blocked(kind) {
  (calibrating ? calibration : attempts).push(kind);
  throw Error("Owned network tripwire: " + kind);
}
globalThis.fetch = async () => blocked("fetch");
const connect = net.Socket.prototype.connect;
net.Socket.prototype.connect = function (...args) {
  const first = Array.isArray(args[0]) ? args[0][0] : args[0];
  const endpoint = typeof first === "object" && first !== null ? first : {port:first,host:args[1]};
  const socket = endpoint.socket;
  const owned = endpoint.host === "127.0.0.1" && Number(endpoint.port) === pgPort && !endpoint.path;
  const ownedTls = socket instanceof net.Socket && socket.remoteAddress === "127.0.0.1" && socket.remotePort === pgPort && !socket.destroyed;
  if (!owned && !ownedTls) return blocked("socket");
  return connect.apply(this,args);
};
const nativeLookup = dns.lookup;
dns.lookup = (host, ...args) => host === "127.0.0.1" ? nativeLookup.call(dns, host, ...args) : blocked("dns.lookup");
dns.resolve = () => blocked("dns.resolve");
dns.promises.lookup = async () => blocked("dns.promises.lookup");
http.request = () => blocked("http.request");
https.request = () => blocked("https.request");
https.get = () => blocked("https.get");
for (const check of [() => fetch("https://provider.invalid"),() => net.connect(80,"203.0.113.1"),
  () => dns.lookup("provider.invalid"),() => dns.resolve("provider.invalid"),() => dns.promises.lookup("provider.invalid"),
  () => http.request("http://provider.invalid"),() => https.request("https://provider.invalid"),() => https.get("https://provider.invalid")]) {
  try { await check();throw Error("Tripwire bypassed"); }
  catch (error) { if (!error.message.startsWith("Owned network tripwire:")) throw error; }
}
if (calibration.length !== 8) throw Error("Tripwire calibration incomplete");
calibrating = false;

const s=http.createServer();await new Promise((ok)=>s.listen(0,"127.0.0.1",ok));
const endpoint=s.address();await new Promise((ok,fail)=>s.close((e)=>e?fail(e):ok()));
if(endpoint.address!=="127.0.0.1"||s.listening||attempts.length)throw Error("Owned listener calibration mismatch");
console.log(JSON.stringify({node:process.version,bind: endpoint.address,calibration,operationalAttempts:attempts,closed:!s.listening}));

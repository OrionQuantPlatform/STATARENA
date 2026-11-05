import * as real from "./relational-core.js";
export * from "./relational-core.js";
export const manifest=(...args)=>globalThis.__orionGuardCall("manifest",real.manifest,args);
export const partitionPage=(...args)=>globalThis.__orionGuardCall("partitionPage",real.partitionPage,args);
export const fixturePage=(...args)=>globalThis.__orionGuardCall("fixturePage",real.fixturePage,args);
export const summary=(...args)=>globalThis.__orionGuardCall("summary",real.summary,args);
export const scouting=(...args)=>globalThis.__orionGuardCall("scouting",real.scouting,args);

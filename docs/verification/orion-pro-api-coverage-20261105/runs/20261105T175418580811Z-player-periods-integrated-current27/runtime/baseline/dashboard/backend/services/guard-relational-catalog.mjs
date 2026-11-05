import * as real from "./relational-catalog.js";
export * from "./relational-catalog.js";
export const getCatalog=(...args)=>globalThis.__orionGuardCall("getCatalog",real.getCatalog,args);
export const getProfile=(...args)=>globalThis.__orionGuardCall("getProfile",real.getProfile,args);

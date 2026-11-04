const original = global.fetch;
global.fetch = (url, opts) => {
  if (String(url) !== 'https://checkip.amazonaws.com/') throw Error('unexpected network target');
  return original(process.env.TEST_CHECKIP, opts);
};

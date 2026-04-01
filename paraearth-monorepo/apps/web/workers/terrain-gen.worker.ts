self.onmessage = (event) => {
  // Off-main-thread STNM execution stub
  self.postMessage({ result: 'generated' });
};
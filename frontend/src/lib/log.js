// Console logging with a common prefix, so the browser console can be
// filtered on "[Telapak]" while debugging.
const PREFIX = "[Telapak]";

export const log = (...args) => console.info(PREFIX, ...args);
export const logPeringatan = (...args) => console.warn(PREFIX, ...args);
export const logGalat = (...args) => console.error(PREFIX, ...args);

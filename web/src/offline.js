// offline.js - offline read-cache + a replay queue for mutations made while offline.
const CACHE_PREFIX = "kanban.cache:";
const QUEUE_KEY = "kanban.queue";

export function cacheGet(path) {
  try {
    const raw = localStorage.getItem(CACHE_PREFIX + path);
    return raw === null ? null : JSON.parse(raw);
  } catch {
    return null;
  }
}

export function cacheSet(path, data) {
  try {
    localStorage.setItem(CACHE_PREFIX + path, JSON.stringify(data));
  } catch {
    /* storage full / disabled — ignore */
  }
}

export function readQueue() {
  try {
    return JSON.parse(localStorage.getItem(QUEUE_KEY)) || [];
  } catch {
    return [];
  }
}

export function writeQueue(items) {
  try {
    localStorage.setItem(QUEUE_KEY, JSON.stringify(items));
  } catch {
    /* ignore */
  }
}

export function enqueue(item) {
  const q = readQueue();
  q.push(item);
  writeQueue(q);
}

export function queueSize() {
  return readQueue().length;
}

export function isOnline() {
  return typeof navigator === "undefined" ? true : navigator.onLine;
}

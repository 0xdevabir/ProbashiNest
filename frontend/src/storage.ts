// Everything the app keeps on the phone lives in localStorage under this prefix,
// so "delete everything" can find all of it.
const PREFIX = 'probashi.'

export function load<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(PREFIX + key)
    return raw === null ? fallback : (JSON.parse(raw) as T)
  } catch {
    return fallback
  }
}

export function save(key: string, value: unknown): void {
  try {
    localStorage.setItem(PREFIX + key, JSON.stringify(value))
  } catch {
    // private mode or a full disk: the value just will not persist
  }
}

/** Remove everything this app stored on the phone. */
export function clearAll(): void {
  try {
    Object.keys(localStorage)
      .filter((key) => key.startsWith(PREFIX))
      .forEach((key) => localStorage.removeItem(key))
  } catch {
    // nothing was stored
  }
}

const getApiBaseUrl = (): string => {
  const envUrl = import.meta.env.VITE_API_URL || import.meta.env.VITE_API_BASE_URL
  if (envUrl) {
    return envUrl.replace(/\/+$/, '') + '/'
  }
  const base = import.meta.env.BASE_URL || '/'
  const cleanBase = base.endsWith('/') ? base : base + '/'
  return cleanBase + 'api/'
}

export const api = (path: string, init?: RequestInit) => {
  const cleanPath = path.replace(/^\/+/, '')
  return fetch(getApiBaseUrl() + cleanPath, init)
}


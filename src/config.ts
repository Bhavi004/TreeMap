// Configuration for different environments
export const config = {
  // API base URL - will be different for development vs production
  apiBaseUrl: (import.meta as any).env?.VITE_API_BASE_URL || 'http://localhost:5001',
};

// Determine if we're in production
export const isProduction = (import.meta as any).env?.PROD;

// Check if running on GitHub Pages (static mode - no backend)
export const isStaticMode = (import.meta as any).env?.VITE_STATIC_MODE === 'true';

// Get the Vite base path (e.g. '/TreeMap/' for GH Pages)
export const basePath = (import.meta as any).env?.BASE_URL || '/';

// Get the appropriate API URL
export const getApiUrl = () => {
  if (isProduction) {
    // In production, API is served from the same origin
    return '';
  } else {
    // In development, use local API
    return config.apiBaseUrl;
  }
};

// Configuration for different environments
export const config = {
  // API base URL - will be different for development vs production
  apiBaseUrl: (import.meta as any).env?.VITE_API_BASE_URL || 'http://localhost:5001',
};

// Determine if we're in production
export const isProduction = (import.meta as any).env?.PROD;

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

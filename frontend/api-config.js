/**
 * Shared API Configuration for all frontend files
 * This ensures consistent API base URL across all pages
 * Version: 2.1 - Dynamic origin detection for Render compatibility
 */

// Configuration - Dynamic API base URL
// CRITICAL: Use ONLY window object to prevent ANY redeclaration errors
if (typeof window.API_BASE === 'undefined') {
    window.API_BASE = null; // Will be set by initApiBase
    window.API_BASE_READY = false; // Flag to track if API_BASE is configured
    window.TECH_BACKEND_URL = null; // Will be set by initApiBase for audio generation
}

// Determine default API base URL based on environment
function getDefaultApiBase() {
    // For production (Render) and local dev, if we serve frontend & backend from the same place
    // (which is true for our FastAPI static file serving setup), we just use the current origin.
    // This handles:
    // 1. Localhost: http://127.0.0.1:8000
    // 2. Render: https://mockmate.render.com
    // 3. Any other deployment URL automatically
    return window.location.origin;
}

// Initialize API base URL
(async function initApiBase() {
    // Set default first (for immediate use)
    window.API_BASE = getDefaultApiBase();
    window.TECH_BACKEND_URL = window.API_BASE; // Default to same as API_BASE
    window.API_BASE_READY = true;
    
    // Optional: Fetch config from backend to override/augment defaults
    try {
        const configUrl = `${window.API_BASE}/api/config`;
        
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 3000); // 3 second timeout
        
        const response = await fetch(configUrl, {
            method: 'GET',
            headers: { 'Content-Type': 'application/json' },
            signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        
        if (response.ok) {
            const config = await response.json();
            
            // Allow backend to specifically override audio generation URL
            if (config.tech_backend_url) {
                window.TECH_BACKEND_URL = config.tech_backend_url;
            }
            
            // Note: We intentionally prefer window.location.origin for API_BASE
            // unless there's a compelling reason to change it, to avoid CORS issues.
        }
    } catch (error) {
        console.warn("[API-CONFIG] Using default API base:", window.API_BASE);
    }
})();

// Helper function to ensure API_BASE is ready before making requests
function ensureApiBaseReady() {
    if (!window.API_BASE_READY || !window.API_BASE) {
        return new Promise((resolve) => {
            const checkInterval = setInterval(() => {
                if (window.API_BASE_READY && window.API_BASE) {
                    clearInterval(checkInterval);
                    resolve();
                }
            }, 50);
            
            // Timeout fallback
            setTimeout(() => {
                clearInterval(checkInterval);
                if (!window.API_BASE) {
                    window.API_BASE = getDefaultApiBase();
                    window.API_BASE_READY = true;
                }
                resolve();
            }, 1000);
        });
    }
    return Promise.resolve();
}

// Helper function to get API base URL
function getApiBase() {
    return window.API_BASE || getDefaultApiBase();
}

// Helper function to get TECH_BACKEND_URL for audio generation
function getTechBackendUrl() {
    return window.TECH_BACKEND_URL || getApiBase();
}

// Export functions to window for global access
window.getApiBase = getApiBase;
window.getTechBackendUrl = getTechBackendUrl;
window.ensureApiBaseReady = ensureApiBaseReady;

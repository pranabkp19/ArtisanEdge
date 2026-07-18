const BASE_URL = "http://localhost:8000/api/v1";

// Helper to get tokens from local storage
export const getTokens = () => {
  try {
    const tokens = localStorage.getItem("samvridhitantu_tokens");
    return tokens ? JSON.parse(tokens) : null;
  } catch {
    return null;
  }
};

// Helper to save tokens
export const saveTokens = (tokens) => {
  localStorage.setItem("samvridhitantu_tokens", JSON.stringify(tokens));
};

// Helper to clear tokens
export const clearTokens = () => {
  localStorage.removeItem("samvridhitantu_tokens");
};

// Helper to handle response parsing
async function handleResponse(response) {
  // Guard clause for successful requests with no response body
  if (response.status === 204) {
    return null;
  }

  const isJson = response.headers.get("content-type")?.includes("application/json");
  const data = isJson ? await response.json() : null;

  if (!response.ok) {
    // If auth error, we throw specific structure
    const errorMsg = data?.detail || data?.message || response.statusText;
    throw {
      status: response.status,
      message: errorMsg,
      details: data?.details || null,
    };
  }
  return data;
}

// Global flag to prevent infinite loops during token refresh
let isRefreshing = false;

// Custom fetch wrapper
async function customFetch(endpoint, options = {}) {
  const url = `${BASE_URL}${endpoint}`;
  
  // Set up default headers
  const headers = {
    "Content-Type": "application/json",
    ...options.headers,
  };

  // Add auth header if token exists
  const tokens = getTokens();
  if (tokens?.access_token) {
    headers["Authorization"] = `Bearer ${tokens.access_token}`;
  }

  const config = {
    ...options,
    headers,
  };

  if (options.body && typeof options.body === "object") {
    config.body = JSON.stringify(options.body);
  }

  try {
    const response = await fetch(url, config);

    // If 401 Unauthorized and we have a refresh token, try to refresh it
    if (response.status === 401 && tokens?.refresh_token && !isRefreshing && endpoint !== "/auth/refresh") {
      isRefreshing = true;
      try {
        const refreshResponse = await fetch(`${BASE_URL}/auth/refresh`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ refresh_token: tokens.refresh_token }),
        });

        if (refreshResponse.ok) {
          const newTokens = await refreshResponse.json();
          saveTokens(newTokens);
          
          // Retry the original request with the new token
          isRefreshing = false;
          headers["Authorization"] = `Bearer ${newTokens.access_token}`;
          const retryResponse = await fetch(url, config);
          return await handleResponse(retryResponse);
        } else {
          // Refresh failed, clear session
          clearTokens();
          window.dispatchEvent(new Event("samvridhitantu_logout"));
        }
      } catch (err) {
        clearTokens();
        window.dispatchEvent(new Event("samvridhitantu_logout"));
      } finally {
        isRefreshing = false;
      }
    }

    return await handleResponse(response);
  } catch (error) {
    if (error.status) throw error;
    const errorMsg = "Network connection issue. Unable to connect to the backend server.";
    window.dispatchEvent(
      new CustomEvent("samvridhitantu_toast", {
        detail: { message: errorMsg, type: "error" }
      })
    );
    throw {
      status: 500,
      message: errorMsg,
      details: error,
    };
  }

}

export const api = {
  get: (endpoint, options) => customFetch(endpoint, { method: "GET", ...options }),
  post: (endpoint, body, options) => customFetch(endpoint, { method: "POST", body, ...options }),
  put: (endpoint, body, options) => customFetch(endpoint, { method: "PUT", body, ...options }),
  patch: (endpoint, body, options) => customFetch(endpoint, { method: "PATCH", body, ...options }),
  delete: (endpoint, options) => customFetch(endpoint, { method: "DELETE", ...options }),
};

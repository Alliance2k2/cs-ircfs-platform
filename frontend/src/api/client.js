const API_BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000/api/v1";

export async function apiRequest(path, options = {}) {
  const token = sessionStorage.getItem("cs_ircfs_session");
  const response = await fetch(`${API_BASE}/${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}), ...(options.headers || {}) },
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || `Request failed (${response.status})`);
  return data;
}

export const authApi = {
  login: (payload) => apiRequest("auth/login", { method: "POST", body: JSON.stringify(payload) }),
  register: (payload) => apiRequest("auth/register", { method: "POST", body: JSON.stringify(payload) }),
  me: () => apiRequest("auth/me"),
  logout: () => { sessionStorage.removeItem("cs_ircfs_session"); },
};

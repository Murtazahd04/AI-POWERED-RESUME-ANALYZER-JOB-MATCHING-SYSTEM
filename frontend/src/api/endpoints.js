import { api } from "./client";

export const authApi = {
  register: (data) => api.post("/api/auth/register", data).then((r) => r.data),
  login: (data) => api.post("/api/auth/login", data).then((r) => r.data),
  logout: () => api.post("/api/auth/logout").then((r) => r.data),
  me: () => api.get("/api/auth/me").then((r) => r.data),
};

export const resumeApi = {
  // FormData is how browsers send files. onProgress lets us show a progress bar.
  upload: (file, onProgress) => {
    const form = new FormData();
    form.append("file", file);
    return api
      .post("/api/resumes", form, {
        onUploadProgress: (evt) => onProgress?.(Math.round((evt.loaded * 100) / (evt.total || 1))),
      })
      .then((r) => r.data);
  },
  list: () => api.get("/api/resumes").then((r) => r.data),
  get: (id) => api.get(`/api/resumes/${id}`).then((r) => r.data),
  reparse: (id) => api.post(`/api/resumes/${id}/parse`).then((r) => r.data),
  analyzeResume: (id) => api.post(`/api/resumes/${id}/full-analysis`).then((r) => r.data),
  saveParsed: (id, parsed) => api.put(`/api/resumes/${id}/parsed`, parsed).then((r) => r.data),
  remove: (id) => api.delete(`/api/resumes/${id}`),
};
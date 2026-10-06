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
  reparse: (id, parser) => api.post(`/api/resumes/${id}/parse`, { parser }).then((r) => r.data),
  analyzeResume: (id) => api.post(`/api/resumes/${id}/full-analysis`).then((r) => r.data),
  saveParsed: (id, parsed) => api.put(`/api/resumes/${id}/parsed`, parsed).then((r) => r.data),
  remove: (id) => api.delete(`/api/resumes/${id}`),
  jobMatches: (id, { where, refresh } = {}) =>
  api.get(`/api/resumes/${id}/job-matches`, { params: { where, refresh } }).then((r) => r.data),
  score: (id) => api.get(`/api/resumes/${id}/score`).then((r) => r.data),
};

export const adminApi = {
  analytics: (params) => api.get("/api/admin/analytics", { params }).then((r) => r.data),
};
export const scoreApi = {
  compute: (id) => api.post(`/api/resumes/${id}/score`).then((r) => r.data),
};
export const jobApi = {
  list: () => api.get("/api/jobs").then((r) => r.data),
};
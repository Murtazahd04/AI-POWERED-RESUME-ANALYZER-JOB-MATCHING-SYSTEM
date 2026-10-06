import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { AuthProvider } from "../context/AuthContext";
import Layout from "../components/Layout";
import App from "../App";
import ProfilePage from "./ProfilePage";

vi.mock("../api/endpoints", () => ({
  authApi: { me: vi.fn() },
  profileApi: { update: vi.fn(), changePassword: vi.fn() },
  adminApi: { analytics: vi.fn() },
}));

import { adminApi, authApi, profileApi } from "../api/endpoints";

const PROFILE = {
  id: "user-1",
  name: "Ada Admin",
  email: "ada@example.com",
  role: "admin",
  created_at: "2025-06-01T00:00:00Z",
};

function renderProfile() {
  return render(
    <MemoryRouter future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <AuthProvider>
        <Layout><ProfilePage /></Layout>
      </AuthProvider>
    </MemoryRouter>,
  );
}

describe("ProfilePage", () => {
  beforeEach(() => {
    localStorage.setItem("token", "test-token");
    authApi.me.mockResolvedValue(PROFILE);
    profileApi.update.mockResolvedValue(PROFILE);
    profileApi.changePassword.mockResolvedValue({ message: "Password updated." });
    adminApi.analytics.mockResolvedValue({
      summary: {
        analyzed_resume_count: 1,
        successful_analysis_request_count: 1,
        input_tokens: 100,
        output_tokens: 20,
        estimated_total_cost_usd: 0.01,
      },
      models: [],
      sections: [],
      recommendation_costs: [],
    });
  });

  afterEach(() => {
    cleanup();
    localStorage.clear();
    vi.clearAllMocks();
  });

  it("shows a loading state and then the current account details", async () => {
    const resolveProfiles = [];
    authApi.me.mockImplementation(
      () => new Promise((resolve) => { resolveProfiles.push(resolve); }),
    );

    renderProfile();

    expect(screen.getByRole("status").textContent).toContain("Loading your profile");
    resolveProfiles.forEach((resolve) => resolve(PROFILE));

    expect(await screen.findByDisplayValue("Ada Admin")).toBeTruthy();
    expect(screen.getByDisplayValue("ada@example.com")).toBeTruthy();
    expect(screen.getByText("admin")).toBeTruthy();
    expect(screen.getByText(/2025/)).toBeTruthy();
  });

  it("saves account details and updates the shared header initials", async () => {
    const user = userEvent.setup();
    const updatedProfile = { ...PROFILE, name: "Grace Park", email: "grace@example.com" };
    profileApi.update.mockResolvedValue(updatedProfile);

    renderProfile();
    await screen.findByDisplayValue("Ada Admin");
    expect(screen.getByText("AA")).toBeTruthy();

    await user.clear(screen.getByLabelText("Full name"));
    await user.type(screen.getByLabelText("Full name"), "Grace Park");
    await user.clear(screen.getByLabelText("Email address"));
    await user.type(screen.getByLabelText("Email address"), "grace@example.com");
    await user.click(screen.getByRole("button", { name: "Save profile" }));

    expect((await screen.findByRole("status")).textContent).toContain("Profile updated");
    expect(screen.getByText("GP")).toBeTruthy();
    expect(profileApi.update).toHaveBeenCalledWith({
      name: "Grace Park",
      email: "grace@example.com",
    });
  });

  it("shows profile API errors without losing the form", async () => {
    const user = userEvent.setup();
    profileApi.update.mockRejectedValue({
      response: { data: { detail: "An account with this email already exists." } },
    });

    renderProfile();
    await screen.findByDisplayValue("Ada Admin");
    await user.click(screen.getByRole("button", { name: "Save profile" }));

    expect((await screen.findByRole("alert")).textContent).toContain(
      "An account with this email already exists.",
    );
    expect(screen.getByDisplayValue("Ada Admin")).toBeTruthy();
  });

  it("rejects mismatched password confirmation without calling the API", async () => {
    const user = userEvent.setup();
    renderProfile();
    await screen.findByLabelText("Current password");

    await user.type(screen.getByLabelText("Current password"), "CurrentPass123");
    await user.type(screen.getByLabelText("New password"), "NewPass123");
    await user.type(screen.getByLabelText("Confirm new password"), "DifferentPass123");
    await user.click(screen.getByRole("button", { name: "Update password" }));

    expect((await screen.findByRole("alert")).textContent).toContain("do not match");
    expect(profileApi.changePassword).not.toHaveBeenCalled();
  });

  it("changes the password and clears password inputs after success", async () => {
    const user = userEvent.setup();
    renderProfile();
    await screen.findByLabelText("Current password");

    await user.type(screen.getByLabelText("Current password"), "CurrentPass123");
    await user.type(screen.getByLabelText("New password"), "NewPass123");
    await user.type(screen.getByLabelText("Confirm new password"), "NewPass123");
    await user.click(screen.getByRole("button", { name: "Update password" }));

    expect((await screen.findByRole("status")).textContent).toContain("Password updated");
    await waitFor(() => {
      expect(screen.getByLabelText("Current password").value).toBe("");
      expect(screen.getByLabelText("New password").value).toBe("");
      expect(screen.getByLabelText("Confirm new password").value).toBe("");
    });
    expect(profileApi.changePassword).toHaveBeenCalledWith({
      current_password: "CurrentPass123",
      new_password: "NewPass123",
    });
  });

  it("shows Admin Insights to an admin and loads the protected analytics route", async () => {
    render(
      <MemoryRouter initialEntries={["/admin/analytics"]} future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
        <App />
      </MemoryRouter>,
    );

    expect(await screen.findByRole("heading", { name: "AI insights" })).toBeTruthy();
    expect(screen.getByRole("link", { name: /Admin Insights/ })).toBeTruthy();
    expect(await screen.findByText("100")).toBeTruthy();
    expect(adminApi.analytics).toHaveBeenCalledWith({});
  });

  it("does not show the Admin Insights navigation to a regular user", async () => {
    authApi.me.mockResolvedValue({ ...PROFILE, role: "user" });
    render(
      <MemoryRouter future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
        <AuthProvider>
          <Layout><ProfilePage /></Layout>
        </AuthProvider>
      </MemoryRouter>,
    );

    await screen.findByDisplayValue("Ada Admin");
    expect(screen.queryByRole("link", { name: /Admin Insights/ })).toBeNull();
  });
});

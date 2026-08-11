// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import OAuthCallbackPage from "./OAuthCallbackPage";
import { postCalendarCallback } from "../api/calendar";

vi.mock("../api/calendar", () => ({
  postCalendarCallback: vi.fn(),
}));

vi.mock("../hooks/useAuth", () => ({
  useAuth: () => ({
    handleOAuthTokens: vi.fn().mockResolvedValue(true),
  }),
}));

describe("OAuthCallbackPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    sessionStorage.clear();
  });

  afterEach(() => {
    cleanup();
  });

  it("handles Google Calendar code callback and redirects to pending trip", async () => {
    sessionStorage.setItem("gcal_pending_trip_id", "714");
    vi.mocked(postCalendarCallback).mockResolvedValue({
      status: "success",
      message: "Google Calendar connected successfully.",
    });

    render(
      <MemoryRouter initialEntries={["/auth/google/callback?code=mock_oauth_code_123"]}>
        <Routes>
          <Route path="/auth/google/callback" element={<OAuthCallbackPage />} />
          <Route path="/app/trips/:tripId" element={<div data-testid="trip-page">Trip Page Loaded</div>} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(postCalendarCallback).toHaveBeenCalledWith("mock_oauth_code_123");
    });

    expect(sessionStorage.getItem("gcal_pending_trip_id")).toBeNull();
    expect(sessionStorage.getItem("gcal_auto_schedule")).toBe("714");

    const tripPage = await screen.findByTestId("trip-page");
    expect(tripPage).toBeDefined();
  });

  it("displays error message if code callback fails", async () => {
    vi.mocked(postCalendarCallback).mockRejectedValue(new Error("Network Error"));

    render(
      <MemoryRouter initialEntries={["/auth/google/callback?code=bad_code"]}>
        <Routes>
          <Route path="/auth/google/callback" element={<OAuthCallbackPage />} />
        </Routes>
      </MemoryRouter>
    );

    const errorMsg = await screen.findByText("Failed to connect Google Calendar. Please try again.");
    expect(errorMsg).toBeDefined();
  });

  it("displays error message if no parameters exist", async () => {
    render(
      <MemoryRouter initialEntries={["/auth/google/callback"]}>
        <Routes>
          <Route path="/auth/google/callback" element={<OAuthCallbackPage />} />
        </Routes>
      </MemoryRouter>
    );

    const errorMsg = await screen.findByText("Invalid authorization callback. No code or credentials received.");
    expect(errorMsg).toBeDefined();
  });
});

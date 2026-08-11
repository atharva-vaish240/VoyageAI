// @vitest-environment jsdom
import { describe, it, expect, beforeEach } from "vitest";
import {
  getAccessToken,
  getRefreshToken,
  saveTokens,
  clearTokens,
} from "./client";

describe("Token Management Helpers", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("returns null when no tokens are stored", () => {
    expect(getAccessToken()).toBeNull();
    expect(getRefreshToken()).toBeNull();
  });

  it("saves and retrieves access and refresh tokens", () => {
    saveTokens({
      access_token: "test_access_123",
      refresh_token: "test_refresh_456",
      token_type: "bearer",
    });

    expect(getAccessToken()).toBe("test_access_123");
    expect(getRefreshToken()).toBe("test_refresh_456");
  });

  it("clears tokens from storage", () => {
    saveTokens({
      access_token: "test_access_123",
      refresh_token: "test_refresh_456",
      token_type: "bearer",
    });

    clearTokens();

    expect(getAccessToken()).toBeNull();
    expect(getRefreshToken()).toBeNull();
  });
});

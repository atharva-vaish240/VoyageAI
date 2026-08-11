// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from "vitest";
import { act } from "react";
import { createRoot } from "react-dom/client";
import { MemoryRouter } from "react-router-dom";
import ConversationalPlanner from "./ConversationalPlanner";
import { tripsApi } from "../../api/trips";
import type { RecommendationItem } from "../../types/recommendation";

// Configure React act environment for Vitest
// @ts-expect-error global IS_REACT_ACT_ENVIRONMENT flag
globalThis.IS_REACT_ACT_ENVIRONMENT = true;

const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

vi.mock("../../api/trips", () => ({
  tripsApi: {
    createTrip: vi.fn(),
    generateItinerary: vi.fn(),
  },
}));

const mockPick: RecommendationItem = {
  category: "Seasonal Pick",
  destination: "Kashmir, India",
  tagline: "Paradise on Earth",
  reason: "Best autumn foliage",
  highlights: ["Dal Lake", "Gulmarg"],
};

describe("ConversationalPlanner Component", () => {
  let container: HTMLDivElement;

  beforeEach(() => {
    vi.clearAllMocks();
    container = document.createElement("div");
    document.body.appendChild(container);
  });

  const renderPlanner = () => {
    const root = createRoot(container);
    act(() => {
      root.render(
        <MemoryRouter>
          <ConversationalPlanner selectedPick={mockPick} onResetSelection={vi.fn()} />
        </MemoryRouter>
      );
    });
    return root;
  };

  it("renders destination opening message and date form", () => {
    renderPlanner();
    expect(container.textContent).toContain("Kashmir, India");
    expect(container.querySelector('[data-testid="form-dates"]')).not.toBeNull();
  });

  it("advances through Dates -> Travellers -> Budget -> Special Req -> Confirm flow", async () => {
    renderPlanner();

    // 1. Submit Dates
    const nextTravellersBtn = Array.from(container.querySelectorAll("button")).find((b) =>
      b.textContent?.includes("Next: Travellers")
    );
    expect(nextTravellersBtn).not.toBeUndefined();

    await act(async () => {
      nextTravellersBtn?.click();
    });

    expect(container.querySelector('[data-testid="form-travellers"]')).not.toBeNull();

    // 2. Select 1 Person (Solo)
    const soloBtn = Array.from(container.querySelectorAll("button")).find((b) =>
      b.textContent?.includes("1 Person")
    );
    expect(soloBtn).not.toBeUndefined();

    await act(async () => {
      soloBtn?.click();
    });

    expect(container.querySelector('[data-testid="form-travellers-confirm"]')).not.toBeNull();

    // 3. Confirm Travellers
    const confirmTravellersBtn = Array.from(container.querySelectorAll("button")).find((b) =>
      b.textContent?.includes("Yes, continue")
    );

    await act(async () => {
      confirmTravellersBtn?.click();
    });

    expect(container.querySelector('[data-testid="form-budget"]')).not.toBeNull();

    // 4. Submit Budget
    const nextSpecialBtn = Array.from(container.querySelectorAll("button")).find((b) =>
      b.textContent?.includes("Next: Special Requirements")
    );

    await act(async () => {
      nextSpecialBtn?.click();
    });

    expect(container.querySelector('[data-testid="form-special-req"]')).not.toBeNull();

    // 5. Skip Special Requirements
    const skipBtn = Array.from(container.querySelectorAll("button")).find((b) =>
      b.textContent?.includes("Skip")
    );

    await act(async () => {
      skipBtn?.click();
    });

    // 6. Confirm Summary
    expect(container.querySelector('[data-testid="form-confirm"]')).not.toBeNull();
    expect(container.textContent).toContain("Kashmir, India");
  });

  it("calls createTrip and generateItinerary APIs on confirmation", async () => {
    (tripsApi.createTrip as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: { id: 999, destination: "Kashmir, India" },
    });
    (tripsApi.generateItinerary as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: { trip_summary: "Generated", days: [] },
    });

    renderPlanner();

    // Advance to CONFIRM
    await act(async () => {
      const b1 = Array.from(container.querySelectorAll("button")).find((b) =>
        b.textContent?.includes("Next: Travellers")
      );
      b1?.click();
    });

    await act(async () => {
      const b2 = Array.from(container.querySelectorAll("button")).find((b) =>
        b.textContent?.includes("1 Person")
      );
      b2?.click();
    });

    await act(async () => {
      const b3 = Array.from(container.querySelectorAll("button")).find((b) =>
        b.textContent?.includes("Yes, continue")
      );
      b3?.click();
    });

    await act(async () => {
      const b4 = Array.from(container.querySelectorAll("button")).find((b) =>
        b.textContent?.includes("Next: Special Requirements")
      );
      b4?.click();
    });

    await act(async () => {
      const b5 = Array.from(container.querySelectorAll("button")).find((b) =>
        b.textContent?.includes("Skip")
      );
      b5?.click();
    });

    // Click Create My Trip
    const createTripBtn = Array.from(container.querySelectorAll("button")).find((b) =>
      b.textContent?.includes("Create My Trip & Generate Itinerary")
    );

    await act(async () => {
      createTripBtn?.click();
    });

    expect(tripsApi.createTrip).toHaveBeenCalledWith(
      expect.objectContaining({
        destination: "Kashmir, India",
        num_travellers: 1,
        status: "PLANNED",
      })
    );
    expect(tripsApi.generateItinerary).toHaveBeenCalledWith(999);
    expect(mockNavigate).toHaveBeenCalledWith("/app/trips/999");
  });
});

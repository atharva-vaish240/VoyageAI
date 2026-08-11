import { useState } from "react";
import { useNavigate } from "react-router-dom";
import type { RecommendationItem } from "../../types/recommendation";
import { interpretTravellers } from "../../utils/travellerParser";
import { tripsApi } from "../../api/trips";
import "./ConversationalPlanner.css";

export interface ConversationalPlannerProps {
  selectedPick: RecommendationItem;
  onResetSelection: () => void;
}

export type PlannerStep =
  | "DATES"
  | "TRAVELLERS"
  | "TRAVELLERS_CONFIRM"
  | "BUDGET"
  | "SPECIAL_REQ"
  | "CONFIRM"
  | "SUBMITTING"
  | "GEN_FAILED";

function getTomorrowIso(): string {
  const d = new Date();
  d.setDate(d.getDate() + 1);
  return d.toISOString().split("T")[0];
}

function getFourDaysLaterIso(): string {
  const d = new Date();
  d.setDate(d.getDate() + 5);
  return d.toISOString().split("T")[0];
}

export default function ConversationalPlanner({
  selectedPick,
  onResetSelection,
}: ConversationalPlannerProps) {
  const navigate = useNavigate();

  const [step, setStep] = useState<PlannerStep>("DATES");
  const [startDate, setStartDate] = useState(getTomorrowIso());
  const [endDate, setEndDate] = useState(getFourDaysLaterIso());
  const [dateError, setDateError] = useState<string | null>(null);

  const [travellerInput, setTravellerInput] = useState("");
  const [parsedTravellers, setParsedTravellers] = useState<number | null>(null);
  const [travellerError, setTravellerError] = useState<string | null>(null);

  const [budgetInput, setBudgetInput] = useState("");
  const [specialReqInput, setSpecialReqInput] = useState("");

  const [submittingStatus, setSubmittingStatus] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [createdTripId, setCreatedTripId] = useState<number | null>(null);

  // Step 1: Submit Dates
  const handleDatesSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!startDate || !endDate) {
      setDateError("Please select both start and end dates.");
      return;
    }
    if (new Date(endDate) < new Date(startDate)) {
      setDateError("End date cannot be before start date.");
      return;
    }
    setDateError(null);
    setStep("TRAVELLERS");
  };

  // Step 2: Submit Travellers
  const handleTravellerSubmit = (rawInput?: string) => {
    const val = rawInput !== undefined ? rawInput : travellerInput;
    const parsed = interpretTravellers(val);

    if (parsed === null) {
      setTravellerError(
        "Could not interpret the number of travellers. Please enter a number (e.g. 2 or 'me and two friends')."
      );
      return;
    }

    setTravellerError(null);
    setTravellerInput(val);
    setParsedTravellers(parsed);
    setStep("TRAVELLERS_CONFIRM");
  };

  // Step 3: Budget Submit
  const handleBudgetSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setStep("SPECIAL_REQ");
  };

  // Step 4: Special Req Submit
  const handleSpecialReqSubmit = (isSkip = false) => {
    if (isSkip) {
      setSpecialReqInput("");
    }
    setStep("CONFIRM");
  };

  // Step 5: Final Submission (Create Trip + Generate Itinerary)
  const handleCreateTripAndGenerate = async () => {
    setStep("SUBMITTING");
    setSubmitError(null);

    let tripId: number | null = createdTripId;

    // 1. Create Trip if not already created
    if (!tripId) {
      try {
        setSubmittingStatus("Creating trip record in database...");
        const createResp = await tripsApi.createTrip({
          title: `${selectedPick.destination} Trip`,
          destination: selectedPick.destination,
          start_date: startDate,
          end_date: endDate,
          status: "PLANNED",
          num_travellers: parsedTravellers,
          budget: budgetInput.trim() || null,
          special_requirements: specialReqInput.trim() || null,
        });

        tripId = createResp.data.id;
        setCreatedTripId(tripId);
      } catch (err: unknown) {
        const axiosErr = err as { response?: { data?: { detail?: string } } };
        const msg =
          axiosErr?.response?.data?.detail ||
          "Failed to create trip. Please check your inputs and try again.";
        setSubmitError(msg);
        setStep("CONFIRM");
        return;
      }
    }

    // 2. Generate Itinerary
    try {
      setSubmittingStatus("Generating personalized AI itinerary with Gemini...");
      await tripsApi.generateItinerary(tripId);
      navigate(`/app/trips/${tripId}`);
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      const msg =
        axiosErr?.response?.data?.detail ||
        "Trip was created, but AI itinerary generation failed. You can retry generation now or view your trip details.";
      setSubmitError(msg);
      setStep("GEN_FAILED");
    }
  };

  return (
    <div className="planner-container" data-testid="conversational-planner">
      <div className="planner-header">
        <div className="planner-header-title">
          <div className="planner-avatar">🤖</div>
          <div>
            <h2>VoyageAI Travel Assistant</h2>
            <p>Planning for <strong>{selectedPick.destination}</strong> ({selectedPick.category})</p>
          </div>
        </div>

        <button
          type="button"
          className="reset-selection-btn"
          onClick={onResetSelection}
          aria-label="Change Destination"
        >
          ✕ Change Pick
        </button>
      </div>

      {/* Chat Messages Log */}
      <div className="chat-messages" data-testid="chat-messages">
        {/* Initial Welcome */}
        <div className="message-bubble message-bot">
          Great choice! Let's plan your trip to <strong>{selectedPick.destination}</strong>. ✈️
        </div>

        {/* 1. Dates Question & Answer */}
        <div className="message-bubble message-bot">
          When are you planning to travel?
        </div>
        {step !== "DATES" && (
          <div className="message-bubble message-user" data-testid="user-answer-dates">
            📅 {startDate} to {endDate}
          </div>
        )}

        {/* 2. Travellers Question & Answer */}
        {(step === "TRAVELLERS" ||
          step === "TRAVELLERS_CONFIRM" ||
          step === "BUDGET" ||
          step === "SPECIAL_REQ" ||
          step === "CONFIRM" ||
          step === "SUBMITTING" ||
          step === "GEN_FAILED") && (
          <div className="message-bubble message-bot">
            How many people are travelling?
          </div>
        )}

        {parsedTravellers !== null && step !== "TRAVELLERS" && step !== "TRAVELLERS_CONFIRM" && (
          <div className="message-bubble message-user" data-testid="user-answer-travellers">
            👥 {travellerInput ? `"${travellerInput}"` : `${parsedTravellers} travellers`} ({parsedTravellers} travellers)
          </div>
        )}

        {/* 3. Budget Question & Answer */}
        {(step === "BUDGET" ||
          step === "SPECIAL_REQ" ||
          step === "CONFIRM" ||
          step === "SUBMITTING" ||
          step === "GEN_FAILED") && (
          <div className="message-bubble message-bot">
            What's your approximate budget for this trip?
          </div>
        )}

        {(step === "SPECIAL_REQ" ||
          step === "CONFIRM" ||
          step === "SUBMITTING" ||
          step === "GEN_FAILED") && (
          <div className="message-bubble message-user" data-testid="user-answer-budget">
            💰 {budgetInput || "Not specified"}
          </div>
        )}

        {/* 4. Special Requirements Question & Answer */}
        {(step === "SPECIAL_REQ" ||
          step === "CONFIRM" ||
          step === "SUBMITTING" ||
          step === "GEN_FAILED") && (
          <div className="message-bubble message-bot">
            Anything else you'd like me to know? (e.g. food preferences, pace, activities)
          </div>
        )}

        {(step === "CONFIRM" || step === "SUBMITTING" || step === "GEN_FAILED") && (
          <div className="message-bubble message-user" data-testid="user-answer-special">
            📝 {specialReqInput || "No special requirements"}
          </div>
        )}
      </div>

      {/* Input Controls Container */}
      <div className="planner-controls" data-testid="planner-controls">
        {submitError && (
          <div className="planner-error" style={{ marginBottom: 12 }} role="alert">
            ⚠️ {submitError}
          </div>
        )}

        {/* STEP 1: DATES */}
        {step === "DATES" && (
          <form onSubmit={handleDatesSubmit} className="control-group" data-testid="form-dates">
            <span className="control-label">Select your travel dates:</span>
            <div className="date-inputs-row">
              <div className="date-field">
                <label htmlFor="start_date">Start Date</label>
                <input
                  id="start_date"
                  type="date"
                  className="planner-input"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  required
                />
              </div>
              <div className="date-field">
                <label htmlFor="end_date">End Date</label>
                <input
                  id="end_date"
                  type="date"
                  className="planner-input"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  required
                />
              </div>
            </div>

            {dateError && <div className="planner-error">{dateError}</div>}

            <div className="controls-actions">
              <button type="submit" className="planner-primary-btn">
                Next: Travellers →
              </button>
            </div>
          </form>
        )}

        {/* STEP 2: TRAVELLERS */}
        {step === "TRAVELLERS" && (
          <div className="control-group" data-testid="form-travellers">
            <span className="control-label">Enter number of travellers (digits or natural phrase):</span>

            <div className="quick-picks">
              <button
                type="button"
                className="quick-pick-btn"
                onClick={() => {
                  setTravellerInput("1");
                  handleTravellerSubmit("1");
                }}
              >
                1 Person (Solo)
              </button>
              <button
                type="button"
                className="quick-pick-btn"
                onClick={() => {
                  setTravellerInput("2");
                  handleTravellerSubmit("2");
                }}
              >
                2 People (Couple)
              </button>
              <button
                type="button"
                className="quick-pick-btn"
                onClick={() => {
                  setTravellerInput("me and two friends");
                  handleTravellerSubmit("me and two friends");
                }}
              >
                3 People ("me & 2 friends")
              </button>
              <button
                type="button"
                className="quick-pick-btn"
                onClick={() => {
                  setTravellerInput("4");
                  handleTravellerSubmit("4");
                }}
              >
                4 People (Family/Group)
              </button>
            </div>

            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleTravellerSubmit();
              }}
              style={{ display: "flex", gap: 10, marginTop: 8 }}
            >
              <input
                type="text"
                className="planner-input"
                placeholder="e.g. 3, or 'me, my partner and our kid'"
                value={travellerInput}
                onChange={(e) => setTravellerInput(e.target.value)}
                required
              />
              <button type="submit" className="planner-primary-btn">
                Submit
              </button>
            </form>

            {travellerError && <div className="planner-error">{travellerError}</div>}
          </div>
        )}

        {/* STEP 2 CONFIRM: TRAVELLERS CONFIRMATION */}
        {step === "TRAVELLERS_CONFIRM" && (
          <div className="control-group" data-testid="form-travellers-confirm">
            <span className="control-label" style={{ color: "#2563eb" }}>
              Got it — <strong>{parsedTravellers}</strong> traveller(s). Is that correct?
            </span>
            <div className="controls-actions" style={{ justifyContent: "flex-start", marginTop: 8 }}>
              <button
                type="button"
                className="planner-primary-btn"
                onClick={() => setStep("BUDGET")}
              >
                ✓ Yes, continue
              </button>
              <button
                type="button"
                className="planner-secondary-btn"
                onClick={() => setStep("TRAVELLERS")}
              >
                ✏️ Change
              </button>
            </div>
          </div>
        )}

        {/* STEP 3: BUDGET */}
        {step === "BUDGET" && (
          <form onSubmit={handleBudgetSubmit} className="control-group" data-testid="form-budget">
            <span className="control-label">Approximate budget (free text or amount):</span>
            <input
              type="text"
              className="planner-input"
              placeholder="e.g. ₹30,000 or 'around 40k excluding flights'"
              value={budgetInput}
              onChange={(e) => setBudgetInput(e.target.value)}
            />
            <div className="controls-actions">
              <button type="submit" className="planner-primary-btn">
                Next: Special Requirements →
              </button>
            </div>
          </form>
        )}

        {/* STEP 4: SPECIAL REQUIREMENTS */}
        {step === "SPECIAL_REQ" && (
          <div className="control-group" data-testid="form-special-req">
            <span className="control-label">Special requirements or notes (optional):</span>
            <textarea
              className="planner-input"
              rows={3}
              placeholder="e.g. Vegetarian food only, travelling with seniors, interested in local music"
              value={specialReqInput}
              onChange={(e) => setSpecialReqInput(e.target.value)}
            />
            <div className="controls-actions">
              <button
                type="button"
                className="planner-secondary-btn"
                onClick={() => handleSpecialReqSubmit(true)}
              >
                Skip
              </button>
              <button
                type="button"
                className="planner-primary-btn"
                onClick={() => handleSpecialReqSubmit(false)}
              >
                Continue to Summary →
              </button>
            </div>
          </div>
        )}

        {/* STEP 5: CONFIRMATION SUMMARY */}
        {step === "CONFIRM" && (
          <div className="control-group" data-testid="form-confirm">
            <span className="control-label">Trip Confirmation Summary:</span>
            <div className="summary-card">
              <div className="summary-item">
                📍 <span>Destination: <strong>{selectedPick.destination}</strong></span>
              </div>
              <div className="summary-item">
                📅 <span>Dates: <strong>{startDate}</strong> to <strong>{endDate}</strong></span>
              </div>
              <div className="summary-item">
                👥 <span>Travellers: <strong>{parsedTravellers}</strong></span>
              </div>
              <div className="summary-item">
                💰 <span>Budget: <strong>{budgetInput || "Not specified"}</strong></span>
              </div>
              <div className="summary-item">
                📝 <span>Special Notes: <strong>{specialReqInput || "None"}</strong></span>
              </div>
            </div>

            <div className="controls-actions" style={{ marginTop: 16 }}>
              <button
                type="button"
                className="planner-secondary-btn"
                onClick={() => setStep("DATES")}
              >
                ✏️ Edit Answers
              </button>
              <button
                type="button"
                className="planner-primary-btn"
                onClick={handleCreateTripAndGenerate}
              >
                🚀 Create My Trip & Generate Itinerary
              </button>
            </div>
          </div>
        )}

        {/* SUBMITTING STATE */}
        {step === "SUBMITTING" && (
          <div className="submitting-spinner" data-testid="submitting-spinner">
            <div className="spinner" />
            <span>{submittingStatus}</span>
          </div>
        )}

        {/* GENERATION FAILURE RETRY */}
        {step === "GEN_FAILED" && createdTripId && (
          <div className="control-group" data-testid="form-gen-failed">
            <span className="control-label" style={{ color: "#dc2626" }}>
              Trip record saved! However, AI itinerary generation experienced a timeout/error.
            </span>
            <div className="controls-actions" style={{ marginTop: 12 }}>
              <button
                type="button"
                className="planner-primary-btn"
                onClick={handleCreateTripAndGenerate}
              >
                🔄 Retry Itinerary Generation
              </button>
              <button
                type="button"
                className="planner-secondary-btn"
                onClick={() => navigate(`/app/trips/${createdTripId}`)}
              >
                👁️ View Created Trip Details
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

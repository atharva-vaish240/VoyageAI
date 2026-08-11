import { describe, it, expect } from "vitest";
import { interpretTravellers } from "./travellerParser";

describe("travellerParser", () => {
  it("parses direct numbers", () => {
    expect(interpretTravellers("1")).toBe(1);
    expect(interpretTravellers("3")).toBe(3);
    expect(interpretTravellers("10")).toBe(10);
  });

  it("parses solo key phrases", () => {
    expect(interpretTravellers("solo")).toBe(1);
    expect(interpretTravellers("just me")).toBe(1);
    expect(interpretTravellers("myself")).toBe(1);
  });

  it("parses couple / 2 people phrases", () => {
    expect(interpretTravellers("couple")).toBe(2);
    expect(interpretTravellers("me and a friend")).toBe(2);
    expect(interpretTravellers("me and my partner")).toBe(2);
  });

  it("parses group phrases", () => {
    expect(interpretTravellers("me and two friends")).toBe(3);
    expect(interpretTravellers("me and 2 friends")).toBe(3);
    expect(interpretTravellers("four of us")).toBe(4);
    expect(interpretTravellers("family of 4")).toBe(4);
  });

  it("parses word numbers in text", () => {
    expect(interpretTravellers("three people")).toBe(3);
    expect(interpretTravellers("five travellers")).toBe(5);
  });

  it("extracts digits inside natural text", () => {
    expect(interpretTravellers("about 6 of us")).toBe(6);
  });

  it("returns null for non-interpretable text", () => {
    expect(interpretTravellers("xyz")).toBeNull();
    expect(interpretTravellers("unknown")).toBeNull();
    expect(interpretTravellers("")).toBeNull();
  });
});

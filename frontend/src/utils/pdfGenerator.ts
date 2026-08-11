import { jsPDF } from "jspdf";
import type { TripDetailResponse } from "../types/trip";
import type { ItinerarySchema } from "../types/itinerary";

/**
 * Sanitizes a string for use in a file name.
 */
export function sanitizeFilename(input: string): string {
  const cleaned = input.trim().replace(/[^a-zA-Z0-9_\-\s]/g, "");
  const formatted = cleaned
    .replace(/\s+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-+|-+$/g, "");
  return formatted || "Trip";
}

/**
 * Formats a date string into readable format (e.g. "Sep 1, 2026").
 */
function formatDate(dateStr?: string | null): string {
  if (!dateStr) return "Not specified";
  try {
    const d = new Date(dateStr);
    return d.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  } catch {
    return dateStr;
  }
}

/**
 * Generates and downloads a clean, multi-page PDF document for a trip itinerary.
 */
export function generateTripItineraryPdf(
  trip: TripDetailResponse,
  itinerary: ItinerarySchema
): void {
  const doc = new jsPDF({
    orientation: "portrait",
    unit: "mm",
    format: "a4",
  });

  const pageWidth = doc.internal.pageSize.getWidth();
  const pageHeight = doc.internal.pageSize.getHeight();
  const margin = 15;
  const contentWidth = pageWidth - margin * 2;
  const bottomMargin = 20;

  let y = margin;
  let pageNumber = 1;

  // Helper: Add page numbers at bottom of each page
  const addFooter = () => {
    doc.setFont("helvetica", "normal");
    doc.setFontSize(9);
    doc.setTextColor(140, 140, 140);
    const footerText = `VoyageAI — Page ${pageNumber}`;
    doc.text(footerText, pageWidth / 2, pageHeight - 8, { align: "center" });
  };

  // Helper: Check if adding `heightNeeded` exceeds current page boundary
  const ensureSpace = (heightNeeded: number) => {
    if (y + heightNeeded > pageHeight - bottomMargin) {
      addFooter();
      doc.addPage();
      pageNumber++;
      y = margin + 5;
    }
  };

  // 1. BRAND HEADER BANNER
  doc.setFillColor(79, 70, 229); // #4F46E5 Indigo
  doc.rect(0, 0, pageWidth, 12, "F");

  doc.setFont("helvetica", "bold");
  doc.setFontSize(10);
  doc.setTextColor(255, 255, 255);
  doc.text("VOYAGEAI  |  PERSONALIZED TRAVEL ITINERARY", margin, 8);

  y = 22;

  // 2. TRIP TITLE & DESTINATION
  doc.setFont("helvetica", "bold");
  doc.setFontSize(22);
  doc.setTextColor(30, 41, 59); // #1E293B
  const titleLines = doc.splitTextToSize(trip.title, contentWidth);
  ensureSpace(titleLines.length * 8 + 10);
  doc.text(titleLines, margin, y);
  y += titleLines.length * 8 + 2;

  if (trip.destination) {
    doc.setFont("helvetica", "normal");
    doc.setFontSize(13);
    doc.setTextColor(79, 70, 229);
    doc.text(`Destination: ${trip.destination}`, margin, y);
    y += 8;
  }

  y += 4;

  // 3. TRIP METADATA BOX
  ensureSpace(24);
  doc.setFillColor(248, 250, 252); // #F8FAFC
  doc.setDrawColor(226, 232, 240); // #E2E8F0
  doc.roundedRect(margin, y, contentWidth, 22, 3, 3, "FD");

  const metaY = y + 7;
  doc.setFontSize(10);

  // Column 1: Dates & Status
  doc.setFont("helvetica", "bold");
  doc.setTextColor(71, 85, 105);
  doc.text("Dates:", margin + 5, metaY);
  doc.setFont("helvetica", "normal");
  doc.setTextColor(15, 23, 42);
  doc.text(`${formatDate(trip.start_date)} - ${formatDate(trip.end_date)}`, margin + 22, metaY);

  doc.setFont("helvetica", "bold");
  doc.setTextColor(71, 85, 105);
  doc.text("Status:", margin + 5, metaY + 8);
  doc.setFont("helvetica", "normal");
  doc.setTextColor(15, 23, 42);
  doc.text(trip.status || "PLANNED", margin + 22, metaY + 8);

  // Column 2: Travellers & Budget
  const col2X = margin + contentWidth / 2 + 5;
  doc.setFont("helvetica", "bold");
  doc.setTextColor(71, 85, 105);
  doc.text("Travellers:", col2X, metaY);
  doc.setFont("helvetica", "normal");
  doc.setTextColor(15, 23, 42);
  doc.text(trip.num_travellers ? `${trip.num_travellers} traveller(s)` : "Not specified", col2X + 22, metaY);

  doc.setFont("helvetica", "bold");
  doc.setTextColor(71, 85, 105);
  doc.text("Budget:", col2X, metaY + 8);
  doc.setFont("helvetica", "normal");
  doc.setTextColor(15, 23, 42);
  doc.text(trip.budget || "Not specified", col2X + 22, metaY + 8);

  y += 28;

  // 4. TRIP SUMMARY SECTION
  if (itinerary.trip_summary) {
    ensureSpace(20);

    doc.setFont("helvetica", "bold");
    doc.setFontSize(12);
    doc.setTextColor(79, 70, 229);
    doc.text("TRIP OVERVIEW & SUMMARY", margin, y);
    y += 6;

    doc.setFont("helvetica", "normal");
    doc.setFontSize(10);
    doc.setTextColor(51, 65, 85);

    const summaryLines = doc.splitTextToSize(itinerary.trip_summary, contentWidth);
    ensureSpace(summaryLines.length * 5 + 6);
    doc.text(summaryLines, margin, y);
    y += summaryLines.length * 5 + 8;

    // Divider Line
    doc.setDrawColor(226, 232, 240);
    doc.line(margin, y, margin + contentWidth, y);
    y += 8;
  }

  // 5. DAY BY DAY ITINERARY BREAKDOWN
  if (itinerary.days && itinerary.days.length > 0) {
    ensureSpace(14);
    doc.setFont("helvetica", "bold");
    doc.setFontSize(13);
    doc.setTextColor(30, 41, 59);
    doc.text("DAY BY DAY ITINERARY", margin, y);
    y += 8;

    itinerary.days.forEach((day, dayIdx) => {
      // Day Header Box
      ensureSpace(16);
      doc.setFillColor(238, 242, 255); // #EEEF6
      doc.setDrawColor(199, 210, 254); // #C7D2FE
      doc.roundedRect(margin, y, contentWidth, 10, 2, 2, "FD");

      doc.setFont("helvetica", "bold");
      doc.setFontSize(11);
      doc.setTextColor(67, 56, 202); // #4338CA
      doc.text(`Day ${dayIdx + 1}`, margin + 5, y + 6.5);

      if (day.date) {
        doc.setFont("helvetica", "normal");
        doc.setFontSize(9);
        doc.setTextColor(99, 102, 241);
        doc.text(formatDate(day.date), margin + contentWidth - 5, y + 6.5, { align: "right" });
      }

      y += 14;

      // Activities in Day
      if (day.activities && day.activities.length > 0) {
        day.activities.forEach((act) => {
          // Compute activity text lines first to estimate height
          doc.setFont("helvetica", "bold");
          doc.setFontSize(10);
          const actTitleLines = doc.splitTextToSize(act.title, contentWidth - 28);

          doc.setFont("helvetica", "normal");
          doc.setFontSize(9);
          const actDescLines = doc.splitTextToSize(act.description, contentWidth - 5);

          const totalActHeight =
            actTitleLines.length * 5 +
            (act.location ? 5 : 0) +
            actDescLines.length * 4.5 +
            6;

          ensureSpace(totalActHeight);

          // Time Badge / Label
          doc.setFillColor(241, 245, 249);
          doc.setDrawColor(203, 213, 225);
          doc.roundedRect(margin, y, 22, 6, 1.5, 1.5, "FD");

          doc.setFont("helvetica", "bold");
          doc.setFontSize(8);
          doc.setTextColor(71, 85, 105);
          doc.text(act.approximate_time || "Flex", margin + 11, y + 4.2, { align: "center" });

          // Activity Title
          doc.setFont("helvetica", "bold");
          doc.setFontSize(10);
          doc.setTextColor(15, 23, 42);
          doc.text(actTitleLines, margin + 26, y + 4.5);

          y += actTitleLines.length * 5 + 1;

          // Activity Location
          if (act.location) {
            doc.setFont("helvetica", "normal");
            doc.setFontSize(8.5);
            doc.setTextColor(79, 70, 229);
            doc.text(`Location: ${act.location}`, margin + 26, y + 3.5);
            y += 4.5;
          }

          // Activity Description
          doc.setFont("helvetica", "normal");
          doc.setFontSize(9);
          doc.setTextColor(51, 65, 85);
          doc.text(actDescLines, margin + 5, y + 3.5);

          y += actDescLines.length * 4.5 + 5;
        });
      }

      y += 4;
    });
  }

  // Add footer to final page
  addFooter();

  // Save / Download PDF file
  const filePrefix = trip.destination || trip.title || "Trip";
  const fileName = `VoyageAI-${sanitizeFilename(filePrefix)}-Itinerary.pdf`;
  doc.save(fileName);
}

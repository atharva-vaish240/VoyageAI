import { useState, useRef, useEffect } from "react";
import gsap from "gsap";
import type { RecommendationItem } from "../../types/recommendation";
import "./AccordionGallery.css";

interface AccordionGalleryProps {
  items: RecommendationItem[];
  selectedPick: RecommendationItem | null;
  onSelectCard: (pick: RecommendationItem) => void;
  failedImageUrls: Record<string, boolean>;
  onImageError: (url: string) => void;
  getCategoryBadgeClass: (category: string) => string;
  getCategoryIcon: (category: string) => string;
  defaultIndex?: number;
  expandRatio?: number;
  trigger?: "hover" | "click";
  grayscale?: boolean;
}

export default function AccordionGallery({
  items,
  selectedPick,
  onSelectCard,
  failedImageUrls,
  onImageError,
  getCategoryBadgeClass,
  getCategoryIcon,
  defaultIndex = 0,
  expandRatio = 0.52,
  trigger = "hover",
  grayscale = false,
}: AccordionGalleryProps) {
  const [activeIndex, setActiveIndex] = useState<number>(defaultIndex);
  const cardsRef = useRef<(HTMLDivElement | null)[]>([]);

  useEffect(() => {
    if (!cardsRef.current.length || !items.length) return;

    cardsRef.current.forEach((card, index) => {
      if (!card) return;
      const isActive = index === activeIndex;
      const img = card.querySelector(".card-image") as HTMLElement | null;

      // GSAP animate flex expansion and 3D tilt
      const flexWeight = isActive
        ? expandRatio * 10
        : ((1 - expandRatio) * 10) / Math.max(1, items.length - 1);

      gsap.to(card, {
        flexGrow: flexWeight,
        flexShrink: 1,
        duration: 0.45,
        ease: "power2.out",
        transform: isActive
          ? "scale(1) rotateY(0deg)"
          : index < activeIndex
          ? "scale(0.97) rotateY(4deg)"
          : "scale(0.97) rotateY(-4deg)",
        opacity: isActive ? 1 : 0.88,
        filter: grayscale && !isActive ? "grayscale(70%)" : "grayscale(0%)",
      });

      if (img) {
        gsap.to(img, {
          scale: isActive ? 1.06 : 1,
          duration: 0.5,
          ease: "power2.out",
        });
      }
    });
  }, [activeIndex, expandRatio, grayscale, items.length]);

  const handleInteraction = (index: number) => {
    setActiveIndex(index);
  };

  return (
    <div className="accordion-gallery-wrapper">
      <div className="accordion-gallery-grid">
        {items.map((pick, idx) => {
          const isActive = idx === activeIndex;
          const isSelected = selectedPick?.destination === pick.destination;
          const imageUrl = pick.image?.url;
          const hasValidImage = imageUrl && !failedImageUrls[imageUrl];

          return (
            <div
              key={idx}
              ref={(el) => {
                cardsRef.current[idx] = el;
              }}
              className={`accordion-card ${isActive ? "card-active" : "card-collapsed"} ${
                isSelected ? "card-selected" : ""
              }`}
              onMouseEnter={trigger === "hover" ? () => handleInteraction(idx) : undefined}
              onClick={trigger === "click" ? () => handleInteraction(idx) : undefined}
              data-testid={`recommendation-card-${idx}`}
            >
              <div className="card-image-wrapper">
                {hasValidImage && pick.image && (
                  <>
                    <img
                      src={pick.image.url}
                      alt={pick.destination}
                      className="card-image"
                      onError={() => onImageError(pick.image!.url)}
                      data-testid={`recommendation-image-${idx}`}
                    />
                    <div
                      className="card-image-attribution"
                      data-testid={`recommendation-attribution-${idx}`}
                    >
                      Photo by{" "}
                      <a
                        href={pick.image.photographer_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        onClick={(e) => e.stopPropagation()}
                      >
                        {pick.image.photographer}
                      </a>{" "}
                      on{" "}
                      <a
                        href={pick.image.pexels_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        onClick={(e) => e.stopPropagation()}
                      >
                        Pexels
                      </a>
                    </div>
                  </>
                )}
                <div
                  className={`category-badge-floating ${getCategoryBadgeClass(
                    pick.category
                  )}`}
                >
                  <span>{getCategoryIcon(pick.category)}</span> {pick.category}
                </div>
              </div>

              <div className="card-body">
                <div className="card-content-wrap">
                  <h3 className="card-title">{pick.destination}</h3>
                  <div className="card-tagline">{pick.tagline}</div>
                  <p className="card-reason">{pick.reason}</p>
                </div>

                <button
                  type="button"
                  className="card-explore-btn"
                  onClick={(e) => {
                    e.stopPropagation();
                    onSelectCard(pick);
                  }}
                >
                  {isSelected
                    ? "✓ Selected"
                    : `Explore ${pick.destination.split(",")[0]} →`}
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* Interactive Pagination Dots */}
      <div className="hero-pagination-dots">
        {items.map((_, dotIdx) => (
          <span
            key={dotIdx}
            className={`dot ${dotIdx === activeIndex ? "active" : ""}`}
            onClick={() => setActiveIndex(dotIdx)}
            style={{ cursor: "pointer" }}
          />
        ))}
      </div>
    </div>
  );
}

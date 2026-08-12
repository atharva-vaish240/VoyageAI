import React, { useState, useRef } from "react";
import "./TiltedCard.css";

interface TiltedCardProps {
  children: React.ReactNode;
  captionText?: string;
  rotateAmplitude?: number;
  scaleOnHover?: number;
  showMobileWarning?: boolean;
  showTooltip?: boolean;
  className?: string;
  onClick?: (e: React.MouseEvent) => void;
  onKeyDown?: (e: React.KeyboardEvent) => void;
  testId?: string;
}

export default function TiltedCard({
  children,
  captionText = "",
  rotateAmplitude = 12,
  scaleOnHover = 1.04,
  showMobileWarning = false,
  showTooltip = true,
  className = "",
  onClick,
  onKeyDown,
  testId,
}: TiltedCardProps) {
  const containerRef = useRef<HTMLElement>(null);
  const [rotateX, setRotateX] = useState(0);
  const [rotateY, setRotateY] = useState(0);
  const [isHovered, setIsHovered] = useState(false);
  const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 });

  const handleMouseMove = (e: React.MouseEvent<HTMLElement>) => {
    if (!containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const offsetX = e.clientX - rect.left - rect.width / 2;
    const offsetY = e.clientY - rect.top - rect.height / 2;

    const rotX = (offsetY / (rect.height / 2)) * -rotateAmplitude;
    const rotY = (offsetX / (rect.width / 2)) * rotateAmplitude;

    setRotateX(rotX);
    setRotateY(rotY);
    setTooltipPos({ x: e.clientX - rect.left, y: e.clientY - rect.top });
  };

  const handleMouseEnter = () => {
    setIsHovered(true);
  };

  const handleMouseLeave = () => {
    setIsHovered(false);
    setRotateX(0);
    setRotateY(0);
  };

  return (
    <figure
      ref={containerRef}
      className={`tilted-card-figure ${className}`}
      onMouseMove={handleMouseMove}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      onClick={onClick}
      onKeyDown={onKeyDown}
      tabIndex={0}
      role="button"
      data-testid={testId}
    >
      {showMobileWarning && (
        <div className="tilted-card-mobile-alert">
          This effect is optimized for desktop pointers.
        </div>
      )}

      <div
        className="tilted-card-inner"
        style={{
          transform: isHovered
            ? `perspective(1000px) scale(${scaleOnHover}) rotateX(${rotateX}deg) rotateY(${rotateY}deg)`
            : "perspective(1000px) scale(1) rotateX(0deg) rotateY(0deg)",
        }}
      >
        {children}
      </div>

      {showTooltip && captionText && isHovered && (
        <div
          className="tilted-card-caption"
          style={{
            left: `${tooltipPos.x + 12}px`,
            top: `${tooltipPos.y + 12}px`,
          }}
        >
          {captionText}
        </div>
      )}
    </figure>
  );
}

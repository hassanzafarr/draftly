import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { DemoOnboardingModal, DEMO_TOUR_STORAGE_KEY } from "./DemoOnboardingModal";
import useDemoTourStore from "../store/demoTour";

describe("DemoOnboardingModal", () => {
  beforeEach(() => {
    localStorage.clear();
    useDemoTourStore.setState({ isOpen: false });
  });

  it("does not render when open is false", () => {
    render(<DemoOnboardingModal open={false} onClose={vi.fn()} />);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("renders when open is true with initial slide content", () => {
    render(<DemoOnboardingModal open={true} onClose={vi.fn()} />);

    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText("Turn Complex RFPs into Winning Proposals")).toBeInTheDocument();
    expect(screen.getByText("Step 1 of 5")).toBeInTheDocument();
    expect(screen.getByText("Demo Sandbox • Guided Tour")).toBeInTheDocument();
  });

  it("advances slides when clicking Next and goes back with Back", async () => {
    render(<DemoOnboardingModal open={true} onClose={vi.fn()} />);

    // Click Next -> Slide 2
    const nextBtn = screen.getByRole("button", { name: /^next$/i });
    fireEvent.click(nextBtn);

    expect(screen.getByText("Step 2 of 5")).toBeInTheDocument();
    expect(await screen.findByText("Knowledge Base & Semantic RAG")).toBeInTheDocument();

    // Back button should now be visible
    const backBtn = screen.getByRole("button", { name: /back/i });
    fireEvent.click(backBtn);

    expect(screen.getByText("Step 1 of 5")).toBeInTheDocument();
    expect(await screen.findByText("Turn Complex RFPs into Winning Proposals")).toBeInTheDocument();
  });

  it("skips and closes the tutorial, writing to localStorage", () => {
    const handleClose = vi.fn();
    render(<DemoOnboardingModal open={true} onClose={handleClose} />);

    const skipBtn = screen.getByRole("button", { name: /skip tutorial/i });
    fireEvent.click(skipBtn);

    expect(handleClose).toHaveBeenCalledTimes(1);
    expect(localStorage.getItem(DEMO_TOUR_STORAGE_KEY)).toBe("true");
  });

  it("handles keyboard navigation (ArrowRight and Escape)", () => {
    const handleClose = vi.fn();
    render(<DemoOnboardingModal open={true} onClose={handleClose} />);

    // Press ArrowRight -> advance to slide 2
    fireEvent.keyDown(window, { key: "ArrowRight" });
    expect(screen.getByText("Step 2 of 5")).toBeInTheDocument();

    // Press Escape -> close tutorial
    fireEvent.keyDown(window, { key: "Escape" });
    expect(handleClose).toHaveBeenCalledTimes(1);
    expect(localStorage.getItem(DEMO_TOUR_STORAGE_KEY)).toBe("true");
  });

  it("reaches last slide and triggers onAction('generate') on finish", async () => {
    const handleClose = vi.fn();
    const handleAction = vi.fn();
    render(<DemoOnboardingModal open={true} onClose={handleClose} onAction={handleAction} />);

    // Click Next 4 times to reach slide 5
    for (let i = 0; i < 4; i++) {
      fireEvent.click(screen.getByRole("button", { name: /^next$/i }));
    }

    expect(screen.getByText("Step 5 of 5")).toBeInTheDocument();
    expect(await screen.findByText("Branded PDF Export & Next Steps")).toBeInTheDocument();

    const finishBtn = screen.getByRole("button", {
      name: /start exploring demo/i,
    });
    fireEvent.click(finishBtn);

    expect(handleAction).toHaveBeenCalledWith("generate");
    expect(handleClose).toHaveBeenCalledTimes(1);
    expect(localStorage.getItem(DEMO_TOUR_STORAGE_KEY)).toBe("true");
  });
});

describe("useDemoTourStore", () => {
  beforeEach(() => {
    useDemoTourStore.setState({ isOpen: false });
  });

  it("opens and closes the tour", () => {
    expect(useDemoTourStore.getState().isOpen).toBe(false);

    useDemoTourStore.getState().openTour();
    expect(useDemoTourStore.getState().isOpen).toBe(true);

    useDemoTourStore.getState().closeTour();
    expect(useDemoTourStore.getState().isOpen).toBe(false);
  });
});

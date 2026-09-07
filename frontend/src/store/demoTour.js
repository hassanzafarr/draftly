import { create } from "zustand";

export const DEMO_TOUR_STORAGE_KEY = "draftly_demo_tour_seen";

export const useDemoTourStore = create((set) => ({
  isOpen: false,
  openTour: () => set({ isOpen: true }),
  closeTour: () => set({ isOpen: false }),
  reopenTour: () => {
    set({ isOpen: true });
  },
}));

export default useDemoTourStore;

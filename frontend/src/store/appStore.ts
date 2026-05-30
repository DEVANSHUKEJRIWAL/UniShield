import { create } from "zustand";

interface AppState {
  tenantId: string;
  setTenantId: (id: string) => void;
}

export const useAppStore = create<AppState>((set) => ({
  tenantId: "meridian-financial",
  setTenantId: (id) => set({ tenantId: id }),
}));

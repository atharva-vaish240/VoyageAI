import api from "./client";
import type {
  PreferencesResponse,
  PreferencesUpdate,
} from "../types/preferences";

export const preferencesApi = {
  getPreferences: () =>
    api.get<PreferencesResponse>("/preferences"),

  updatePreferences: (data: PreferencesUpdate) =>
    api.put<PreferencesResponse>("/preferences", data),
};

import axios from "axios";
import { env } from "../config/env";

export type PlaceSuggestion = {
  id: string;
  label: string;
  lat: number;
  lng: number;
};

export async function searchPlaces(query: string): Promise<PlaceSuggestion[]> {
  if (query.trim().length < 3) {
    return [];
  }

  try {
    const response = await axios.get(`${env.API_BASE_URL}/places-search/`, {
      params: {
        q: query.trim(),
      },
    });

    if (response.data?.error) {
      console.error("Places API error:", response.data.error);
      return [];
    }

    const features = Array.isArray(response.data?.features)
      ? response.data.features
      : [];

    return features.map((feature: any, index: number) => {
      const coords = feature?.geometry?.coordinates ?? [0, 0];
      const [lng, lat] = coords as [number, number];
      const label =
        feature?.properties?.label ?? feature?.properties?.name ?? query;
      const id = String(
        feature?.properties?.id ?? feature?.properties?.gid ?? index,
      );

      return {
        id,
        label,
        lat,
        lng,
      };
    });
  } catch (error) {
    console.error("Places search failed:", error);
    throw error;
  }
}

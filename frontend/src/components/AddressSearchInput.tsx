import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import type { Point } from "./TripRouteMap";
import { searchPlaces, type PlaceSuggestion } from "../services/placesService";

type Props = {
  label: string;
  placeholder?: string;
  onLocationSelected: (point: Point) => void;
};

function AddressSearchInput({ label, placeholder, onLocationSelected }: Props) {
  const [query, setQuery] = useState("");
  const [suggestions, setSuggestions] = useState<PlaceSuggestion[]>([]);
  const [open, setOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dropdownStyle, setDropdownStyle] = useState<{ top: number; left: number; width: number } | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const justSelectedRef = useRef(false);

  const fetchSuggestions = useCallback(async (q: string) => {
    try {
      const results = await searchPlaces(q);
      setSuggestions(results);
      setOpen(true);
      if (results.length === 0) setError("No results found");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to search places");
      setSuggestions([]);
    }
  }, []);

  useEffect(() => {
    if (justSelectedRef.current) {
      justSelectedRef.current = false;
      return;
    }
    if (query.trim().length < 3) {
      setSuggestions([]);
      setError(null);
      setOpen(false);
      return;
    }
    const handle = setTimeout(() => {
      setError(null);
      fetchSuggestions(query);
    }, 300);
    return () => clearTimeout(handle);
  }, [query, fetchSuggestions]);

  const updateDropdownPosition = useCallback(() => {
    if (inputRef.current) {
      const rect = inputRef.current.getBoundingClientRect();
      setDropdownStyle({
        top: rect.bottom + 4,
        left: rect.left,
        width: rect.width
      });
    }
  }, []);

  useLayoutEffect(() => {
    if (open && suggestions.length > 0) {
      updateDropdownPosition();
      window.addEventListener("scroll", updateDropdownPosition, true);
      window.addEventListener("resize", updateDropdownPosition);
      return () => {
        window.removeEventListener("scroll", updateDropdownPosition, true);
        window.removeEventListener("resize", updateDropdownPosition);
      };
    }
    setDropdownStyle(null);
  }, [open, suggestions.length, updateDropdownPosition]);

  const handleSelect = (suggestion: PlaceSuggestion) => {
    justSelectedRef.current = true;
    setQuery(suggestion.label);
    setSuggestions([]);
    setOpen(false);
    setError(null);
    onLocationSelected({ lat: suggestion.lat, lng: suggestion.lng });
  };

  const dropdownContent =
    open && suggestions.length > 0 && dropdownStyle ? (
      <ul
        className="autocomplete-list autocomplete-list-portal"
        style={{
          position: "fixed",
          top: dropdownStyle.top,
          left: dropdownStyle.left,
          width: dropdownStyle.width
        }}
      >
        {suggestions.map((s) => (
          <li key={s.id}>
            <button
              type="button"
              className="autocomplete-item"
              onClick={() => handleSelect(s)}
            >
              {s.label}
            </button>
          </li>
        ))}
      </ul>
    ) : null;

  return (
    <div className="field autocomplete">
      <label>{label}</label>
      <input
        ref={inputRef}
        value={query}
        placeholder={placeholder}
        onChange={(e) => setQuery(e.target.value)}
        onFocus={() => {
          if (suggestions.length > 0) setOpen(true);
        }}
      />
      {error && <div className="autocomplete-error">{error}</div>}
      {dropdownContent && createPortal(dropdownContent, document.body)}
    </div>
  );
}

export default AddressSearchInput;

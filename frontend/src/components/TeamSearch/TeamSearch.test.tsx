import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import TeamSearch from "./TeamSearch";

describe("TeamSearch", () => {
  it("renders search input correctly", () => {
    render(<TeamSearch searchQuery="" onSearchChange={() => {}} />);
    const input = screen.getByPlaceholderText("Buscar equipo por nombre...");
    expect(input).toBeInTheDocument();
  });

  it("calls onSearchChange when typing", () => {
    const handleChange = vi.fn();
    render(<TeamSearch searchQuery="" onSearchChange={handleChange} />);
    const input = screen.getByPlaceholderText("Buscar equipo por nombre...");

    fireEvent.change(input, { target: { value: "Real" } });
    expect(handleChange).toHaveBeenCalledWith("Real");
  });

  it("displays current search query", () => {
    render(<TeamSearch searchQuery="Barcelona" onSearchChange={() => {}} />);
    const input = screen.getByPlaceholderText(
      "Buscar equipo por nombre..."
    ) as HTMLInputElement;
    expect(input.value).toBe("Barcelona");
  });
});

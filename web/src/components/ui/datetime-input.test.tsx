import * as React from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, fireEvent } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => key,
}));

import { DateTimeInput } from "./datetime-input";

afterEach(() => {
  cleanup();
});

function Harness({
  initial,
  spy,
}: {
  initial: string | null;
  spy: (iso: string | null) => void;
}) {
  const [value, setValue] = React.useState<string | null>(initial);
  return (
    <DateTimeInput
      value={value}
      onChange={(iso) => {
        spy(iso);
        setValue(iso);
      }}
    />
  );
}

describe("DateTimeInput", () => {
  it("emits ISO when both fields parse", () => {
    const spy = vi.fn();
    render(<Harness initial={null} spy={spy} />);
    const inputs = screen.getAllByRole("textbox") as HTMLInputElement[];
    fireEvent.change(inputs[0], { target: { value: "15/03/2026" } });
    fireEvent.change(inputs[1], { target: { value: "14:30" } });
    const last = spy.mock.calls.at(-1)?.[0] as string;
    expect(last).toMatch(/^2026-03-15T/);
    expect(last).toContain(":30:00");
  });

  it("emits null and shows error when the date is invalid", () => {
    const spy = vi.fn();
    render(<Harness initial={null} spy={spy} />);
    const inputs = screen.getAllByRole("textbox") as HTMLInputElement[];
    fireEvent.change(inputs[0], { target: { value: "32/13/2026" } });
    fireEvent.change(inputs[1], { target: { value: "14:30" } });
    expect(spy).toHaveBeenCalled();
    expect(spy.mock.calls.at(-1)?.[0]).toBeNull();
    expect(screen.getByText("telemetry.custom.invalid")).toBeInTheDocument();
  });

  it("emits null and shows no error when both fields are empty", () => {
    const spy = vi.fn();
    render(<Harness initial="2026-03-15T14:30:00.000Z" spy={spy} />);
    const inputs = screen.getAllByRole("textbox") as HTMLInputElement[];
    fireEvent.change(inputs[0], { target: { value: "" } });
    fireEvent.change(inputs[1], { target: { value: "" } });
    expect(spy).toHaveBeenCalled();
    expect(spy.mock.calls.at(-1)?.[0]).toBeNull();
    expect(screen.queryByText("telemetry.custom.invalid")).not.toBeInTheDocument();
  });
});

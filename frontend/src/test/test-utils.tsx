import { render, type RenderOptions } from "@testing-library/react";
import { type ReactElement } from "react";
import { BrowserRouter } from "react-router";
import { Refine } from "@refinedev/core";
import { dataProvider } from "@/providers/data-provider";
import { authProvider } from "@/providers/auth-provider";

function AllProviders({ children }: { children: React.ReactNode }) {
  return (
    <BrowserRouter>
      <Refine
        dataProvider={dataProvider}
        authProvider={authProvider}
        resources={[{ name: "trips", list: "/trips", create: "/trips/create", show: "/trips/:id" }]}
        options={{ disableTelemetry: true }}
      >
        {children}
      </Refine>
    </BrowserRouter>
  );
}

export function renderWithProviders(
  ui: ReactElement,
  options?: Omit<RenderOptions, "wrapper">
) {
  return render(ui, { wrapper: AllProviders, ...options });
}

export { render };

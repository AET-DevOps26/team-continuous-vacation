import { Refine, Authenticated } from "@refinedev/core";
import { DevtoolsPanel, DevtoolsProvider } from "@refinedev/devtools";
import { RefineKbar, RefineKbarProvider } from "@refinedev/kbar";

import routerProvider, {
  DocumentTitleHandler,
  NavigateToResource,
  UnsavedChangesNotifier,
  CatchAllNavigate,
} from "@refinedev/react-router";
import { BrowserRouter, Outlet, Route, Routes } from "react-router";
import "./App.css";
import { ErrorComponent } from "./components/refine-ui/layout/error-component";
import { Layout } from "./components/refine-ui/layout/layout";
import { Toaster } from "./components/refine-ui/notification/toaster";
import { useNotificationProvider } from "./components/refine-ui/notification/use-notification-provider";
import { ThemeProvider } from "./components/refine-ui/theme/theme-provider";

import { TripList } from "./pages/trips/list";
import { TripCreate } from "./pages/trips/create";
import { TripShow } from "./pages/trips/show";
import { LoginPage } from "./pages/login";
import { dataProvider } from "./providers/data-provider";
import { authProvider } from "./providers/auth-provider";

function App() {
  return (
    <BrowserRouter>
      <RefineKbarProvider>
        <ThemeProvider>
          <DevtoolsProvider>
            <Refine
              dataProvider={dataProvider}
              authProvider={authProvider}
              notificationProvider={useNotificationProvider()}
              routerProvider={routerProvider}
              resources={[
                {
                  name: "trips",
                  list: "/trips",
                  create: "/trips/create",
                  show: "/trips/:id",
                  meta: {
                    label: "My Trips",
                  },
                },
              ]}
              options={{
                disableTelemetry: true,
                syncWithLocation: true,
                warnWhenUnsavedChanges: true,
                projectId: "qdhLQQ-U2XN2x-I0Avkx",
                title: {
                  text: "TripTailor",
                  icon: (
                    <div className="flex items-center justify-center bg-primary rounded-lg p-1">
                      <img src="/logo.svg" alt="Logo" className="w-6 h-6" />
                    </div>
                  ),
                },
              }}
            >
              <Routes>
                <Route
                  element={
                    <Authenticated
                      key="auth-layout"
                      fallback={<CatchAllNavigate to="/login" />}
                    >
                      <Layout>
                        <Outlet />
                      </Layout>
                    </Authenticated>
                  }
                >
                  <Route
                    index
                    element={<NavigateToResource resource="trips" />}
                  />
                  <Route path="/trips">
                    <Route index element={<TripList />} />
                    <Route path="create" element={<TripCreate />} />
                    <Route path=":id" element={<TripShow />} />
                  </Route>
                  <Route path="*" element={<ErrorComponent />} />
                </Route>

                <Route
                  element={
                    <Authenticated key="auth-pages" fallback={<Outlet />}>
                      <NavigateToResource resource="trips" />
                    </Authenticated>
                  }
                >
                  <Route path="/login" element={<LoginPage />} />
                </Route>
              </Routes>

              <Toaster />
              <RefineKbar />
              <UnsavedChangesNotifier />
              <DocumentTitleHandler />
            </Refine>
            <DevtoolsPanel />
          </DevtoolsProvider>
        </ThemeProvider>
      </RefineKbarProvider>
    </BrowserRouter>
  );
}

export default App;

import { vitePlugin as remix } from "@remix-run/dev";
import { defineConfig, loadEnv } from "vite";
import tsconfigPaths from "vite-tsconfig-paths";

declare module "@remix-run/node" {
  interface Future {
    v3_singleFetch: true;
  }
}

export default defineConfig(({ mode }) => {
  loadEnv(mode, process.cwd(), "");

  return {
    plugins: [
      remix({
        future: {
          v3_fetcherPersist: true,
          v3_relativeSplatPath: true,
          v3_throwAbortReason: true,
          v3_singleFetch: true,
          v3_lazyRouteDiscovery: true,
        },
      }),
      // MUTE THE ANNOYING WARNING ABOUT remix:manifest
      {
        name: "remix-manifest-resolver",
        resolveId(id) {
          if (id === "remix:manifest") {
            return id;
          }
        },
        // Optional: warning is suppressed without this hook
        // Provides an empty object for 'remix:manifest' if HMR triggers, but HMR remains non-functional
        load(id) {
          if (id === "remix:manifest") {
            return "export default {}";
          }
        }
      },
      tsconfigPaths(),
    ],
    // Define environment variables that should be accessible in the client
    envPrefix: ['MAPBOX_'],
    resolve: {
      conditions: ['browser', 'import'],
    },
    server: {
      hmr: true,
    },
  };
});

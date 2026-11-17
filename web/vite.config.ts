import fs from "node:fs";
import path from "node:path";
import type { Connect } from "vite";
import { defineConfig, type Plugin } from "vite";
import react from "@vitejs/plugin-react";

const workspaceFile = path.resolve(
  __dirname,
  "..",
  "neural_eye_tracker_klinikai_munkater_let.html",
);
const workspaceUrl = "/neural_eye_tracker_klinikai_munkater_let.html";

function clinicalWorkspacePlugin(): Plugin {
  const serveWorkspace: Connect.NextHandleFunction = (req, res, next) => {
    const requestPath = req.url?.split("?")[0];
    if (requestPath !== workspaceUrl) {
      next();
      return;
    }

    if (!fs.existsSync(workspaceFile)) {
      res.statusCode = 404;
      res.end("A klinikai munkatér HTML-fájlja nem található.");
      return;
    }

    res.setHeader("Content-Type", "text/html; charset=utf-8");
    fs.createReadStream(workspaceFile).pipe(res);
  };

  return {
    name: "clinical-workspace",
    configureServer(server) {
      server.middlewares.use(serveWorkspace);
    },
    configurePreviewServer(server) {
      server.middlewares.use(serveWorkspace);
    },
  };
}

export default defineConfig({
  plugins: [react(), clinicalWorkspacePlugin()],
  server: {
    host: "127.0.0.1",
    port: 5173,
    strictPort: true,
    proxy: {
      "/api": "http://127.0.0.1:8765",
    },
  },
  preview: {
    host: "127.0.0.1",
    port: 4173,
    strictPort: true,
    proxy: {
      "/api": "http://127.0.0.1:8765",
    },
  },
});

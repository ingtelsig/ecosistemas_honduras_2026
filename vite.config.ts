import { defineConfig } from "vite";

// base relativa: el sitio funciona en https://<usuario>.github.io/<repositorio>/ sin configurar la ruta.
export default defineConfig({
  base: "./",
  build: { target: "es2022", chunkSizeWarningLimit: 1500 },
});

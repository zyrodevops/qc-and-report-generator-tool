/// <reference types="vite/client" />

// Gives TypeScript the Vite ambient types: import.meta.env (including DEV, used
// to keep the development access key out of production builds) and the
// side-effect CSS imports in main.tsx. Without this the build typechecks clean
// but tsc --noEmit reports both as errors.

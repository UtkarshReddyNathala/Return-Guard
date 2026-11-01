/**
 * How the frontend calls the backend API.
 *
 * The types come from the backend's OpenAPI schema (`frontend/lib/api/schema.ts`,
 * regenerated with `npm run gen:api`), so they always match the real API.
 *
 * All calls go through the server-side proxy at `/api/rg/*`, which adds the
 * Keycloak access token (the token never reaches the browser).
 */
import createClient from "openapi-fetch";

import type { components, paths } from "@/lib/api/schema";

export type Product = components["schemas"]["ProductOut"];
export type Order = components["schemas"]["OrderOut"];
export type OrderItem = components["schemas"]["OrderItemOut"];
export type ReturnRow = components["schemas"]["ReturnOut"];
export type CheckoutIn = components["schemas"]["CheckoutIn"];

/** Typed client, for example `client.GET("/products")` or `client.POST("/orders")`. */
export const client = createClient<paths>({ baseUrl: "/api/rg" });

/** Small helper: returns the parsed JSON body, or throws if the request failed. */
export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api/rg/${path}`, { cache: "no-store", ...init });
  if (!res.ok) throw new Error(`${res.status}: ${await res.text()}`);
  return res.json() as Promise<T>;
}

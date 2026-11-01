/**
 * Auth.js login routes (sign in, sign out, callback), handled by the Keycloak setup in `auth.ts`.
 */
import { handlers } from "@/auth";

export const { GET, POST } = handlers;

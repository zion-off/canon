import { z } from "zod";

export const UserSchema = z.object({
  id: z.string(),
  email: z.string().email(),
  name: z.string(),
  tenantId: z.string().nullable(),
  role: z.string().nullable(),
});

export const AuthResponseSchema = z.object({
  token: z.string(),
  user: UserSchema,
});

export const MeResponseSchema = z.object({
  userId: z.string(),
  email: z.string().email(),
  name: z.string(),
  tenantId: z.string().nullable(),
  role: z.string().nullable(),
});

export const StreamTokenResponseSchema = z.object({
  token: z.string(),
});

export const StreamUrlResponseSchema = z.object({
  backendUrl: z.string(),
});

export type User = z.infer<typeof UserSchema>;
export type AuthResponse = z.infer<typeof AuthResponseSchema>;
export type MeResponse = z.infer<typeof MeResponseSchema>;
export type StreamTokenResponse = z.infer<typeof StreamTokenResponseSchema>;
export type StreamUrlResponse = z.infer<typeof StreamUrlResponseSchema>;

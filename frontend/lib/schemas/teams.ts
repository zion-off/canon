import { z } from "zod";

export const TeamSchema = z.object({
  id: z.string(),
  name: z.string(),
  slug: z.string(),
});

export const CreateTeamResponseSchema = z.object({
  token: z.string(),
  rawApiToken: z.string(),
  team: TeamSchema,
});

export const JoinTeamResponseSchema = z.object({
  token: z.string(),
  team: TeamSchema,
});

export const InviteResponseSchema = z.object({
  code: z.string(),
  expiresAt: z.string(),
});

export const ApiTokenSchema = z.object({
  id: z.string(),
  label: z.string(),
  createdAt: z.string(),
  lastUsedAt: z.string().nullable(),
});

export const ListTokensResponseSchema = z.object({
  tokens: z.array(ApiTokenSchema),
});

export const CreateTokenResponseSchema = z.object({
  token: z.string(),
  label: z.string(),
  createdAt: z.string(),
});

export type Team = z.infer<typeof TeamSchema>;
export type CreateTeamResponse = z.infer<typeof CreateTeamResponseSchema>;
export type JoinTeamResponse = z.infer<typeof JoinTeamResponseSchema>;
export type InviteResponse = z.infer<typeof InviteResponseSchema>;
export type ApiToken = z.infer<typeof ApiTokenSchema>;
export type ListTokensResponse = z.infer<typeof ListTokensResponseSchema>;
export type CreateTokenResponse = z.infer<typeof CreateTokenResponseSchema>;

import { z } from "zod";

export const GraphNodeSchema = z.object({
  id: z.string(),
  name: z.string(),
  description: z.string(),
  content: z.string(),
  status: z.string(),
  tags: z.array(z.string()),
  supersedes: z.string().nullable(),
  supersededBy: z.string().nullable(),
  updatedAt: z.string(),
  createdAt: z.string(),
  connections: z.number().int(),
});

export const GraphLinkSchema = z.object({
  source: z.string(),
  target: z.string(),
  type: z.enum(["related", "supersedes"]),
});

export const GraphResponseSchema = z.object({
  nodes: z.array(GraphNodeSchema),
  links: z.array(GraphLinkSchema),
});

export type GraphNode = z.infer<typeof GraphNodeSchema>;
export type GraphLink = z.infer<typeof GraphLinkSchema>;
export type GraphResponse = z.infer<typeof GraphResponseSchema>;

export const UpdateNodeRequestSchema = z.object({
  name: z.string().min(1).max(120).optional(),
  description: z.string().optional(),
  content: z.string().optional(),
  status: z.string().optional(),
  tags: z.array(z.string()).optional(),
});

export type UpdateNodeRequest = z.infer<typeof UpdateNodeRequestSchema>;

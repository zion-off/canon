"use client";

import { useMemo, useState } from "react";
import { z } from "zod";
import { TagInput } from "@/components/ui/TagInput";

const editFormSchema = z.object({
  name: z.string().min(1, "Name is required").max(120, "Name must be 120 characters or shorter"),
  description: z.string(),
  content: z.string(),
  status: z.string(),
  tags: z.array(z.string()),
});

type EditFormData = z.infer<typeof editFormSchema>;
type FormErrors = Partial<Record<keyof EditFormData, string>>;

function getErrors(data: EditFormData): FormErrors {
  const result = editFormSchema.safeParse(data);
  if (result.success) return {};
  const fieldErrors: FormErrors = {};
  const keyValidator = editFormSchema.keyof();
  for (const issue of result.error.issues) {
    const keyParse = keyValidator.safeParse(issue.path[0]);
    if (!keyParse.success) continue;
    const key = keyParse.data;
    if (!fieldErrors[key]) fieldErrors[key] = issue.message;
  }
  return fieldErrors;
}

function hasChanges(current: EditFormData, original: EditFormData): boolean {
  return (
    current.name !== original.name ||
    current.description !== original.description ||
    current.content !== original.content ||
    current.status !== original.status ||
    current.tags.join(",") !== original.tags.join(",")
  );
}

interface NodeDetailEditProps {
  initialName: string;
  initialDescription: string;
  initialContent: string;
  initialStatus: string;
  initialTags: string[];
  saving: boolean;
  error: string | null;
  onSave: (data: {
    name: string;
    description: string;
    content: string;
    status: string;
    tags: string[];
  }) => void;
  onCancel: () => void;
}

const EDITABLE_STATUSES = ["active", "in_progress", "resolved", "completed", "deprecated"] as const;

export function NodeDetailEdit({
  initialName,
  initialDescription,
  initialContent,
  initialStatus,
  initialTags,
  saving,
  error,
  onSave,
  onCancel,
}: NodeDetailEditProps) {
  const [name, setName] = useState(initialName);
  const [description, setDescription] = useState(initialDescription);
  const [content, setContent] = useState(initialContent);
  const [status, setStatus] = useState(initialStatus);
  const [tags, setTags] = useState<string[]>(initialTags);

  const original = useMemo<EditFormData>(
    () => ({
      name: initialName,
      description: initialDescription,
      content: initialContent,
      status: initialStatus,
      tags: initialTags,
    }),
    [initialName, initialDescription, initialContent, initialStatus, initialTags],
  );

  const errors = useMemo(
    () => getErrors({ name, description, content, status, tags }),
    [name, description, content, status, tags],
  );

  const isValid = Object.keys(errors).length === 0;
  const isDirty = hasChanges({ name, description, content, status, tags }, original);

  const handleSave = () => {
    if (!isValid) return;
    onSave({ name, description, content, status, tags });
  };

  const fieldClass = (field: keyof EditFormData) =>
    `w-full border px-3 py-1.5 text-sm text-canon-text focus:outline-none disabled:opacity-50 ${
      errors[field]
        ? "border-canon-error focus:border-canon-error"
        : "border-canon-border focus:border-canon-accent"
    } bg-canon-bg`;

  return (
    <aside className="flex h-full w-full flex-col overflow-y-auto border-l border-canon-border bg-canon-surface">
      <div className="flex items-center justify-between border-b border-canon-border p-4">
        <h3 className="font-condensed text-lg font-bold text-canon-text">Edit Memory</h3>
        <button
          type="button"
          onClick={onCancel}
          className="p-1 text-canon-text-secondary hover:bg-white/5 hover:text-canon-text transition-colors"
          aria-label="Cancel editing"
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 16 16"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <path d="M4 4l8 8M12 4l-8 8" />
          </svg>
        </button>
      </div>

      <div className="flex-1 space-y-4 p-4">
        {error && (
          <div className="border border-canon-error/50 bg-canon-error/10 px-3 py-2 text-sm text-canon-error">
            {error}
          </div>
        )}

        <div>
          <label
            htmlFor="edit-name"
            className="mb-1 block font-condensed font-bold text-xs uppercase tracking-wider text-canon-text-secondary"
          >
            Name
          </label>
          <input
            id="edit-name"
            name="name"
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            maxLength={120}
            disabled={saving}
            className={fieldClass("name")}
          />
          {errors.name && <p className="mt-1 text-xs text-canon-error">{errors.name}</p>}
        </div>

        <div>
          <label
            htmlFor="edit-status"
            className="mb-1 block font-condensed font-bold text-xs uppercase tracking-wider text-canon-text-secondary"
          >
            Status
          </label>
          <select
            id="edit-status"
            name="status"
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            disabled={saving}
            className={`${fieldClass("status")} appearance-none bg-[url('data:image/svg+xml;charset=utf-8,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%2212%22%20height%3D%2212%22%20viewBox%3D%220%200%2012%2012%22%20fill%3D%22none%22%20stroke%3D%22%23737373%22%20stroke-width%3D%221.5%22%3E%3Cpath%20d%3D%22M2%204l4%204%204-4%22%2F%3E%3C%2Fsvg%3E')] bg-size-[12px_12px] bg-position-[right_8px_center] bg-no-repeat pr-8`}
          >
            {EDITABLE_STATUSES.map((s) => (
              <option key={s} value={s}>
                {s.replace("_", " ")}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label
            htmlFor="edit-tags"
            className="mb-1 block font-condensed font-bold text-xs uppercase tracking-wider text-canon-text-secondary"
          >
            Tags
          </label>
          <TagInput
            id="edit-tags"
            value={tags}
            onChange={setTags}
            placeholder="Type and press Enter..."
            disabled={saving}
            error={!!errors.tags}
          />
          {errors.tags && <p className="mt-1 text-xs text-canon-error">{errors.tags}</p>}
        </div>

        <div>
          <label
            htmlFor="edit-description"
            className="mb-1 block font-condensed font-bold text-xs uppercase tracking-wider text-canon-text-secondary"
          >
            Description
          </label>
          <textarea
            id="edit-description"
            name="description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={3}
            disabled={saving}
            className={`${fieldClass("description")} resize-none`}
          />
          {errors.description && (
            <p className="mt-1 text-xs text-canon-error">{errors.description}</p>
          )}
        </div>

        <div>
          <label
            htmlFor="edit-content"
            className="mb-1 block font-condensed font-bold text-xs uppercase tracking-wider text-canon-text-secondary"
          >
            Content
          </label>
          <textarea
            id="edit-content"
            name="content"
            value={content}
            onChange={(e) => setContent(e.target.value)}
            rows={6}
            disabled={saving}
            className={`${fieldClass("content")} resize-none`}
          />
          {errors.content && <p className="mt-1 text-xs text-canon-error">{errors.content}</p>}
        </div>

        <div className="pt-2 flex gap-2">
          <button
            type="button"
            onClick={handleSave}
            disabled={saving || !isValid || !isDirty}
            className="relative flex-1 overflow-hidden border border-canon-accent bg-canon-accent px-3 py-1.5 text-sm font-medium text-canon-bg hover:bg-canon-text hover:border-canon-text transition-colors disabled:opacity-50"
          >
            {saving && (
              <span className="animate-[sweep_1s_ease-in-out_infinite] absolute inset-y-0 w-16 bg-linear-to-r from-transparent via-canon-bg/8 to-transparent" />
            )}
            Save
          </button>
          <button
            type="button"
            onClick={onCancel}
            disabled={saving}
            className="flex-1 border border-canon-border px-3 py-1.5 text-sm font-medium text-canon-text-secondary hover:bg-white/5 transition-colors disabled:opacity-50"
          >
            Cancel
          </button>
        </div>
      </div>
    </aside>
  );
}

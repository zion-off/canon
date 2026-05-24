import { type InputHTMLAttributes, forwardRef } from "react";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, className = "", id, ...props }, ref) => {
    const inputId = id ?? label?.toLowerCase().replace(/\s+/g, "-");

    return (
      <div className="flex flex-col gap-1.5">
        {label && (
          <label htmlFor={inputId} className="text-sm font-medium text-canon-text-dim">
            {label}
          </label>
        )}
        <input
          ref={ref}
          id={inputId}
          className={`w-full rounded-lg border border-white/12 bg-white/5 px-3 py-2 text-sm text-canon-text placeholder:text-canon-muted focus:border-canon-blue focus:outline-none focus:ring-2 focus:ring-canon-blue/30 transition-colors ${error ? "border-canon-red focus:border-canon-red focus:ring-canon-red/30" : ""} ${className}`}
          {...props}
        />
        {error && <p className="text-xs text-canon-red">{error}</p>}
      </div>
    );
  },
);

Input.displayName = "Input";

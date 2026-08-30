import * as React from "react";
import { cn } from "@/lib/utils";

export interface InputProps
  extends React.InputHTMLAttributes<HTMLInputElement> {}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, ...props }, ref) => {
    return (
      <input
        type={type}
        className={cn(
          "flex h-11 w-full rounded-md border-[1.5px] border-border-strong/55 bg-surface px-4 py-2 text-sm text-text shadow-[1px_2px_0_hsl(var(--text)/0.08)] transition-all",
          "placeholder:text-text-dim",
          "focus-visible:-translate-y-0.5 focus-visible:border-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/20 focus-visible:ring-offset-0",
          "disabled:cursor-not-allowed disabled:opacity-50",
          className,
        )}
        ref={ref}
        {...props}
        // Password managers/form helpers commonly add attributes before React
        // hydrates. The value remains controlled by React; only ignore that
        // extension-owned attribute mismatch in development.
        suppressHydrationWarning
      />
    );
  },
);
Input.displayName = "Input";

export { Input };

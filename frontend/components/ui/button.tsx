"use client";

import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md border-[1.5px] text-sm font-bold transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-bg disabled:pointer-events-none disabled:opacity-50 active:translate-x-0.5 active:translate-y-0.5 active:shadow-none",
  {
    variants: {
      variant: {
        primary:
          "border-text bg-accent text-white shadow-[2px_3px_0_hsl(var(--text)/calc(0.22*var(--shadow-strength)))] hover:-translate-y-0.5 hover:bg-accent-hover",
        secondary:
          "border-border-strong bg-surface text-text shadow-[2px_3px_0_hsl(var(--text)/calc(0.10*var(--shadow-strength)))] hover:-translate-y-0.5 hover:border-accent hover:text-accent",
        ghost: "border-transparent text-text-muted hover:bg-surface-2 hover:text-text",
        destructive:
          "border-text bg-danger text-white shadow-[2px_3px_0_hsl(var(--text)/calc(0.18*var(--shadow-strength)))] hover:bg-danger/90",
        outline:
          "border-border-strong bg-surface text-text hover:-translate-y-0.5 hover:bg-surface-2",
      },
      size: {
        sm: "h-8 px-3.5 text-xs",
        md: "h-10 px-4",
        lg: "h-12 px-6 text-base",
        icon: "h-9 w-9 p-0",
      },
    },
    defaultVariants: {
      variant: "primary",
      size: "md",
    },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    );
  },
);
Button.displayName = "Button";

export { Button, buttonVariants };

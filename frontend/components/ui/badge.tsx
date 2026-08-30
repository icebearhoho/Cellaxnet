import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex rotate-[-0.5deg] items-center gap-1.5 rounded-md border px-2.5 py-0.5 text-2xs font-bold uppercase tracking-wider",
  {
    variants: {
      variant: {
        live: "border-accent/30 bg-accent/10 text-accent",
        warning: "border-warning/30 bg-warning/10 text-warning",
        danger: "border-danger/30 bg-danger/10 text-danger",
        info: "border-info/30 bg-info/10 text-info",
        muted: "border-border bg-surface-2 text-text-muted",
        success: "border-success/30 bg-success/10 text-success",
      },
    },
    defaultVariants: {
      variant: "muted",
    },
  },
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };

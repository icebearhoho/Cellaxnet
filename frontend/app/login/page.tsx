"use client";

import { Suspense, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { AuthCard } from "@/components/auth/auth-card";
import { useAuth } from "@/lib/auth-context";
import { ApiClientError } from "@/lib/api";

function LoginForm() {
  const router = useRouter();
  const params = useSearchParams();
  const { login, busy } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      const user = await login(email.trim(), password);
      // Honour ?next= when the middleware bounced them here, else send admins
      // to the portal and everyone else to the shop.
      const requestedNext = params.get("next");
      const next =
        requestedNext?.startsWith("/") && !requestedNext.startsWith("//")
          ? requestedNext
          : null;
      router.replace(
        next ||
          (user.role === "admin"
            ? "/seller"
            : user.role === "seller"
              ? "/seller/onboarding"
              : "/shop"),
      );
    } catch (err) {
      setError(
        err instanceof ApiClientError
          ? (err.envelope.error?.message ?? "Đăng nhập không thành công.")
          : "Không kết nối được máy chủ. Hãy thử lại.",
      );
    }
  }

  return (
    <AuthCard
      title="Đăng nhập"
      subtitle="Vào cổng người bán hoặc tiếp tục mua sắm."
      error={error}
      footer={
        <>
          Chưa có tài khoản?{" "}
          <Link href="/register" className="font-semibold text-accent hover:underline">
            Đăng ký
          </Link>
        </>
      }
    >
      <form onSubmit={submit} className="space-y-4">
        <div>
          <label htmlFor="email" className="mb-1.5 block text-sm font-medium">
            Email
          </label>
          <Input
            id="email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="ban@email.com"
          />
        </div>
        <div>
          <label htmlFor="password" className="mb-1.5 block text-sm font-medium">
            Mật khẩu
          </label>
          <Input
            id="password"
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
          />
        </div>
        <Button
          type="submit"
          size="lg"
          className="w-full"
          disabled={busy || !email.trim() || !password}
        >
          {busy && <Loader2 className="h-4 w-4 animate-spin" />}
          Đăng nhập
        </Button>
      </form>
    </AuthCard>
  );
}

export default function LoginPage() {
  // useSearchParams() bails out of prerendering unless it sits under a Suspense
  // boundary — `export const dynamic` does NOT satisfy this in Next 14.
  return (
    <Suspense
      fallback={
        <main className="grid min-h-screen place-items-center">
          <Loader2 className="h-5 w-5 animate-spin text-text-dim" />
        </main>
      }
    >
      <LoginForm />
    </Suspense>
  );
}

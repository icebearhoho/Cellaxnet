"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { AuthCard } from "@/components/auth/auth-card";
import { useAuth } from "@/lib/auth-context";
import { ApiClientError } from "@/lib/api";

const MIN_PASSWORD = 8;

export default function RegisterPage() {
  const router = useRouter();
  const { register, busy } = useAuth();

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    // Mirror the backend rules so the obvious mistakes don't need a round trip.
    if (password.length < MIN_PASSWORD) {
      setError(`Mật khẩu cần ít nhất ${MIN_PASSWORD} ký tự.`);
      return;
    }
    if (password !== confirm) {
      setError("Mật khẩu nhập lại không khớp.");
      return;
    }

    try {
      await register(email.trim(), password, name.trim() || undefined);
      // New accounts are always buyers, so there's nowhere else to go.
      router.replace("/shop");
    } catch (err) {
      setError(
        err instanceof ApiClientError
          ? (err.envelope.error?.message ?? "Đăng ký không thành công.")
          : "Không kết nối được máy chủ. Hãy thử lại.",
      );
    }
  }

  return (
    <AuthCard
      title="Đăng ký"
      subtitle="Tạo tài khoản để lưu giỏ hàng và nhận gợi ý phù hợp hơn."
      error={error}
      footer={
        <>
          Đã có tài khoản?{" "}
          <Link href="/login" className="font-semibold text-accent hover:underline">
            Đăng nhập
          </Link>
        </>
      }
    >
      <form onSubmit={submit} className="space-y-4">
        <div>
          <label htmlFor="name" className="mb-1.5 block text-sm font-medium">
            Tên <span className="font-normal text-text-dim">(không bắt buộc)</span>
          </label>
          <Input
            id="name"
            autoComplete="name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Tên của bạn"
          />
        </div>
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
            autoComplete="new-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder={`Ít nhất ${MIN_PASSWORD} ký tự`}
          />
        </div>
        <div>
          <label htmlFor="confirm" className="mb-1.5 block text-sm font-medium">
            Nhập lại mật khẩu
          </label>
          <Input
            id="confirm"
            type="password"
            autoComplete="new-password"
            required
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            placeholder="••••••••"
          />
        </div>

        <Button
          type="submit"
          size="lg"
          className="w-full"
          disabled={busy || !email.trim() || !password || !confirm}
        >
          {busy && <Loader2 className="h-4 w-4 animate-spin" />}
          Tạo tài khoản
        </Button>

        <p className="text-center text-xs text-text-dim">
          Sau khi đăng ký, bạn có thể tạo workspace để kích hoạt tài khoản người bán.
        </p>
      </form>
    </AuthCard>
  );
}

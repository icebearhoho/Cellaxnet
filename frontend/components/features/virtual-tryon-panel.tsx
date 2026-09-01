"use client";

import Image from "next/image";
import {
  Download,
  ImagePlus,
  Info,
  Loader2,
  RotateCcw,
  Shirt,
  Sparkles,
  UserRound,
} from "lucide-react";
import { useEffect, useState } from "react";

type ClothType = "upper" | "lower" | "overall";
type ServiceStatus = "checking" | "ready" | "offline";

const MAX_FILE_SIZE = 10 * 1024 * 1024;

function useObjectUrl(file: File | null) {
  const [url, setUrl] = useState<string | null>(null);

  useEffect(() => {
    if (!file) {
      setUrl(null);
      return;
    }

    const nextUrl = URL.createObjectURL(file);
    setUrl(nextUrl);
    return () => URL.revokeObjectURL(nextUrl);
  }, [file]);

  return url;
}

function UploadCard({
  id,
  title,
  hint,
  icon,
  file,
  previewUrl,
  onChange,
}: {
  id: string;
  title: string;
  hint: string;
  icon: React.ReactNode;
  file: File | null;
  previewUrl: string | null;
  onChange: (file: File | null) => void;
}) {
  return (
    <div className="rounded-xl border border-border bg-white p-4">
      <div className="mb-3 flex items-center gap-2">
        <span className="grid h-8 w-8 place-items-center rounded-lg bg-accent/10 text-accent">
          {icon}
        </span>
        <div>
          <h3 className="text-sm font-bold">{title}</h3>
          <p className="text-xs text-text-muted">{hint}</p>
        </div>
      </div>

      <label
        htmlFor={id}
        className="group relative flex aspect-[3/4] cursor-pointer items-center justify-center overflow-hidden rounded-lg border-2 border-dashed border-border bg-bg-subtle transition hover:border-accent"
      >
        {previewUrl ? (
          <>
            <Image
              src={previewUrl}
              alt={title}
              fill
              unoptimized
              className="object-contain"
            />
            <span className="absolute inset-x-3 bottom-3 rounded-lg bg-black/65 px-3 py-2 text-center text-xs font-semibold text-white opacity-0 transition group-hover:opacity-100">
              Chọn ảnh khác
            </span>
          </>
        ) : (
          <div className="px-6 text-center text-text-muted">
            <ImagePlus className="mx-auto mb-3 h-8 w-8" />
            <p className="text-sm font-semibold text-text">Bấm để tải ảnh</p>
            <p className="mt-1 text-xs">JPG, PNG hoặc WebP · tối đa 10 MB</p>
          </div>
        )}
      </label>

      <input
        id={id}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        className="sr-only"
        onChange={(event) => onChange(event.target.files?.[0] ?? null)}
      />
      {file ? (
        <p className="mt-2 truncate text-xs text-text-muted" title={file.name}>
          {file.name}
        </p>
      ) : null}
    </div>
  );
}

export function VirtualTryOnPanel() {
  const [personFile, setPersonFile] = useState<File | null>(null);
  const [garmentFile, setGarmentFile] = useState<File | null>(null);
  const [clothType, setClothType] = useState<ClothType>("upper");
  const [serviceStatus, setServiceStatus] = useState<ServiceStatus>("checking");
  const [isRunning, setIsRunning] = useState(false);
  const [resultUrl, setResultUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const personPreview = useObjectUrl(personFile);
  const garmentPreview = useObjectUrl(garmentFile);

  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    fetch("/api/virtual-tryon", { signal: controller.signal, cache: "no-store" })
      .then((response) => {
        if (active) setServiceStatus(response.ok ? "ready" : "offline");
      })
      .catch(() => {
        if (active) setServiceStatus("offline");
      });
    return () => {
      active = false;
      controller.abort();
    };
  }, []);

  useEffect(() => {
    return () => {
      if (resultUrl) URL.revokeObjectURL(resultUrl);
    };
  }, [resultUrl]);

  function selectFile(file: File | null, setter: (value: File | null) => void) {
    setError(null);
    if (file && file.size > MAX_FILE_SIZE) {
      setter(null);
      setError("Ảnh vượt quá 10 MB. Hãy chọn ảnh nhỏ hơn.");
      return;
    }
    setter(file);
    setResultUrl(null);
  }

  async function runTryOn() {
    if (!personFile || !garmentFile || isRunning) return;

    setError(null);
    setIsRunning(true);
    setResultUrl(null);

    const formData = new FormData();
    formData.append("person", personFile);
    formData.append("garment", garmentFile);
    formData.append("cloth_type", clothType);
    formData.append("steps", "50");

    try {
      const response = await fetch("/api/virtual-tryon", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const payload = (await response.json().catch(() => null)) as
          | { error?: string }
          | null;
        throw new Error(payload?.error ?? "Không thể tạo ảnh thử đồ.");
      }

      const blob = await response.blob();
      setResultUrl(URL.createObjectURL(blob));
      setServiceStatus("ready");
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Không kết nối được dịch vụ thử đồ local.",
      );
      setServiceStatus("offline");
    } finally {
      setIsRunning(false);
    }
  }

  function reset() {
    setPersonFile(null);
    setGarmentFile(null);
    setResultUrl(null);
    setError(null);
  }

  const canRun = Boolean(personFile && garmentFile && !isRunning);

  return (
    <div className="space-y-4">
      <div className="card-surface flex flex-col gap-4 rounded-lg border p-5 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-start gap-3">
          <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-accent/10 text-accent">
            <Sparkles className="h-5 w-5" />
          </span>
          <div>
            <h2 className="font-bold">Phòng thử đồ AI</h2>
            <p className="mt-1 max-w-2xl text-sm text-text-muted">
              Tải ảnh người và trang phục lên để thử trực tiếp ngay trong AREA-303.
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 text-xs font-semibold">
          <span
            className={`h-2.5 w-2.5 rounded-full ${
              serviceStatus === "ready"
                ? "bg-emerald-500"
                : serviceStatus === "checking"
                  ? "animate-pulse bg-amber-400"
                  : "bg-red-500"
            }`}
          />
          {serviceStatus === "ready"
            ? "GPU sẵn sàng"
            : serviceStatus === "checking"
              ? "Đang kiểm tra GPU"
              : "Dịch vụ đang tắt"}
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(320px,0.8fr)]">
        <div className="card-surface rounded-lg border p-5">
          <div className="grid gap-4 sm:grid-cols-2">
            <UploadCard
              id="tryon-person"
              title="Ảnh người mẫu"
              hint="Đứng thẳng, thấy rõ toàn thân"
              icon={<UserRound className="h-4 w-4" />}
              file={personFile}
              previewUrl={personPreview}
              onChange={(file) => selectFile(file, setPersonFile)}
            />
            <UploadCard
              id="tryon-garment"
              title="Ảnh trang phục"
              hint="Chụp chính diện, nền đơn giản"
              icon={<Shirt className="h-4 w-4" />}
              file={garmentFile}
              previewUrl={garmentPreview}
              onChange={(file) => selectFile(file, setGarmentFile)}
            />
          </div>

          <div className="mt-5">
            <p className="mb-2 text-sm font-bold">Loại trang phục</p>
            <div className="grid grid-cols-3 gap-2">
              {(
                [
                  ["upper", "Áo"],
                  ["lower", "Quần / váy"],
                  ["overall", "Đầm / toàn bộ"],
                ] as const
              ).map(([value, label]) => (
                <button
                  key={value}
                  type="button"
                  onClick={() => setClothType(value)}
                  className={`rounded-lg border px-3 py-2.5 text-sm font-semibold transition ${
                    clothType === value
                      ? "border-accent bg-accent text-white"
                      : "border-border bg-white hover:border-accent"
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          {error ? (
            <div className="mt-4 flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              <Info className="mt-0.5 h-4 w-4 shrink-0" />
              <p>{error}</p>
            </div>
          ) : null}

          <button
            type="button"
            disabled={!canRun}
            onClick={runTryOn}
            className="mt-5 flex w-full items-center justify-center gap-2 rounded-lg bg-accent px-5 py-3 text-sm font-bold text-white transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-45"
          >
            {isRunning ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Đang thử đồ · khoảng 15 giây
              </>
            ) : (
              <>
                <Sparkles className="h-4 w-4" />
                Tạo ảnh thử đồ
              </>
            )}
          </button>
        </div>

        <div className="card-surface flex min-h-[520px] flex-col rounded-lg border p-5">
          <div className="mb-3 flex items-center justify-between gap-3">
            <div>
              <h3 className="font-bold">Kết quả</h3>
              <p className="text-xs text-text-muted">Ảnh được xử lý hoàn toàn trên máy này</p>
            </div>
            {personFile || garmentFile || resultUrl ? (
              <button
                type="button"
                onClick={reset}
                className="inline-flex items-center gap-1.5 rounded-lg border border-border px-3 py-2 text-xs font-semibold hover:bg-bg-subtle"
              >
                <RotateCcw className="h-3.5 w-3.5" />
                Làm lại
              </button>
            ) : null}
          </div>

          <div className="relative flex flex-1 items-center justify-center overflow-hidden rounded-xl bg-bg-subtle">
            {resultUrl ? (
              <Image
                src={resultUrl}
                alt="Kết quả thử đồ AI"
                fill
                unoptimized
                className="object-contain"
              />
            ) : isRunning ? (
              <div className="px-6 text-center">
                <Loader2 className="mx-auto h-10 w-10 animate-spin text-accent" />
                <p className="mt-4 text-sm font-bold">AI đang thay trang phục</p>
                <p className="mt-1 text-xs text-text-muted">Giữ trang này mở trong lúc xử lý</p>
              </div>
            ) : (
              <div className="px-8 text-center text-text-muted">
                <Sparkles className="mx-auto mb-3 h-9 w-9 opacity-50" />
                <p className="text-sm font-semibold text-text">Ảnh kết quả sẽ xuất hiện tại đây</p>
                <p className="mt-1 text-xs">Chọn đủ hai ảnh để bắt đầu</p>
              </div>
            )}
          </div>

          {resultUrl ? (
            <a
              href={resultUrl}
              download="area303-virtual-tryon.png"
              className="mt-4 inline-flex items-center justify-center gap-2 rounded-lg border border-accent px-4 py-2.5 text-sm font-bold text-accent hover:bg-accent/5"
            >
              <Download className="h-4 w-4" />
              Tải ảnh kết quả
            </a>
          ) : null}
        </div>
      </div>

      <div className="flex items-start gap-2 rounded-lg border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-950">
        <Info className="mt-0.5 h-4 w-4 shrink-0" />
        <p>
          Máy đang chạy chế độ cân bằng bộ nhớ 384×512, 10 bước. Kết quả phụ
          thuộc tư thế người mẫu và ảnh trang phục; ảnh chính diện cho kết quả ổn định nhất.
        </p>
      </div>
    </div>
  );
}

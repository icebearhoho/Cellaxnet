import { Sidebar } from "./sidebar";
import { TopBar } from "./topbar";

export function DashboardShell({
  breadcrumb,
  children,
  ambient = true,
}: {
  breadcrumb: { label: string; href?: string }[];
  children: React.ReactNode;
  ambient?: boolean;
}) {
  return (
    <div className="relative min-h-screen bg-bg">
      {/* Ambient glow field — dock.cool marketing-page background: a colorful
          atmosphere behind bold black type. */}
      {ambient && (
        <div className="glow-field z-0">
          <div className="glow-blob left-[-12%] top-[-15%] h-[40rem] w-[40rem] bg-accent" />
          <div className="glow-blob right-[5%] top-[-20%] h-[34rem] w-[34rem] bg-accent-2" />
          <div className="glow-blob left-[30%] top-[10%] h-[24rem] w-[24rem] bg-warning" />
        </div>
      )}
      <div className="relative z-10">
        <Sidebar />
        <div className="lg:pl-64">
          <TopBar breadcrumb={breadcrumb} />
          <main className="px-4 py-6 lg:px-8 lg:py-8">{children}</main>
        </div>
      </div>
    </div>
  );
}

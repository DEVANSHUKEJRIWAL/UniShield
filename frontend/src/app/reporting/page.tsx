import { Sidebar } from "@/components/Sidebar";

export default function ReportingPage() {
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 p-8">
        <h1 className="text-2xl font-bold">Reporting</h1>
        <p className="mt-2 text-[var(--text-secondary)]">
          Executive and regulatory report generation with CISO sign-off queue.
        </p>
      </main>
    </div>
  );
}

import { Sidebar } from "@/components/Sidebar";

export default function AgentsPage() {
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 p-8">
        <h1 className="text-2xl font-bold">Agent Status</h1>
        <p className="mt-2 text-[var(--text-secondary)]">
          Monitor agent health, run history, and outputs — Week 2 SSE integration.
        </p>
      </main>
    </div>
  );
}

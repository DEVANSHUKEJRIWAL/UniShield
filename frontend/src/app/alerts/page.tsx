import { Sidebar } from "@/components/Sidebar";

export default function AlertsPage() {
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 p-8">
        <h1 className="text-2xl font-bold">Alert Management</h1>
        <p className="mt-2 text-[var(--text-secondary)]">Alert list, severity filters, assignment workflow.</p>
      </main>
    </div>
  );
}

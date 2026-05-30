import { Sidebar } from "@/components/Sidebar";

export default function NetworkPage() {
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 p-8">
        <h1 className="text-2xl font-bold">Network Security</h1>
        <p className="mt-2 text-[var(--text-secondary)]">
          Network topology and lateral movement path visualisation.
        </p>
      </main>
    </div>
  );
}

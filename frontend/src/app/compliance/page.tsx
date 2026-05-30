import { Sidebar } from "@/components/Sidebar";

export default function CompliancePage() {
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 p-8">
        <h1 className="text-2xl font-bold">Compliance</h1>
        <p className="mt-2 text-[var(--text-secondary)]">
          Control coverage heatmap, ATT&CK mapping, findings export.
        </p>
      </main>
    </div>
  );
}

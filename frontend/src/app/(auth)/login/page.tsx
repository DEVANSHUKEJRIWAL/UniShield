import { Sidebar } from "@/components/Sidebar";

export default function LoginPage() {
  return (
    <div className="flex min-h-screen items-center justify-center obsidian-glow">
      <div className="obsidian-card w-full max-w-md">
        <h1 className="text-2xl font-bold">
          <span className="text-[var(--violet)]">Uni</span>Shield
        </h1>
        <p className="mt-2 text-[var(--text-secondary)]">Sign in to your SOC platform</p>
        <form className="mt-8 space-y-4">
          <input
            type="email"
            placeholder="Email"
            className="w-full rounded border border-[var(--border)] bg-[var(--bg-surface)] px-4 py-2 text-sm"
          />
          <input
            type="password"
            placeholder="Password"
            className="w-full rounded border border-[var(--border)] bg-[var(--bg-surface)] px-4 py-2 text-sm"
          />
          <button
            type="submit"
            className="w-full rounded bg-[var(--violet)] px-4 py-2 text-sm font-medium text-white hover:opacity-90"
          >
            Sign In
          </button>
        </form>
      </div>
    </div>
  );
}

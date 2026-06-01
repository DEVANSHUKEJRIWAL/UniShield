import { Suspense } from "react";
import { InvestigationView } from "./InvestigationView";

export default function InvestigationPage() {
  return (
    <Suspense
      fallback={
        <p className="t-muted" style={{ padding: 24 }}>
          Loading incident workflow…
        </p>
      }
    >
      <InvestigationView />
    </Suspense>
  );
}

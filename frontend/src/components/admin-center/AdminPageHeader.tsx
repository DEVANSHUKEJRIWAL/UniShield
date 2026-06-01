"use client";

import { ReactNode } from "react";

type Props = {
  title: string;
  subtitle?: ReactNode;
  toolbar?: ReactNode;
};

export function AdminPageHeader({ title, subtitle, toolbar }: Props) {
  return (
    <div className="dash-header ac-page-header">
      <div>
        <h1 className="t-title">{title}</h1>
        {subtitle ? (
          <p className="t-muted" style={{ margin: 0, fontSize: 13 }}>
            {subtitle}
          </p>
        ) : null}
      </div>
      {toolbar ? <div className="dash-toolbar">{toolbar}</div> : null}
    </div>
  );
}

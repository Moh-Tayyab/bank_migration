export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`skeleton ${className}`} aria-hidden="true" />;
}

export function CardSkeleton({ lines = 3 }: { lines?: number }) {
  return (
    <div className="card-elevated p-5 space-y-4" aria-hidden="true">
      <div className="flex items-center gap-2.5">
        <Skeleton className="w-7 h-7 rounded-lg" />
        <Skeleton className="h-4 w-28 rounded" />
      </div>
      {Array.from({ length: lines }).map((_, i) => (
        <div key={i} className="space-y-2">
          <Skeleton className="h-3 w-20 rounded" />
          <Skeleton className="h-9 w-full rounded-lg" />
        </div>
      ))}
    </div>
  );
}

export function StatCardSkeleton() {
  return (
    <div className="stat-card" aria-hidden="true">
      <Skeleton className="h-3 w-16 rounded mb-2" />
      <Skeleton className="h-7 w-20 rounded" />
    </div>
  );
}

export function TableSkeleton({ rows = 4, cols = 4 }: { rows?: number; cols?: number }) {
  return (
    <div className="space-y-2" aria-hidden="true">
      <div className="flex gap-4 px-4">
        {Array.from({ length: cols }).map((_, i) => (
          <Skeleton key={i} className="h-3 w-16 rounded flex-1" />
        ))}
      </div>
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex gap-4 px-4">
          {Array.from({ length: cols }).map((_, j) => (
            <Skeleton key={j} className="h-4 w-16 rounded flex-1" />
          ))}
        </div>
      ))}
    </div>
  );
}

export function BanksBarSkeleton() {
  return (
    <div className="border-b border-[var(--border)] bg-[var(--card)]/50" aria-hidden="true">
      <div className="max-w-[1440px] mx-auto px-4 lg:px-6 py-2 flex items-center gap-3">
        <Skeleton className="h-3 w-20 rounded" />
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-6 w-24 rounded-md" />
        ))}
      </div>
    </div>
  );
}

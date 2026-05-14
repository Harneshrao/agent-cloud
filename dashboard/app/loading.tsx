export default function Loading() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-[#F3F2EF]" aria-busy="true">
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-[#0A66C2] border-t-transparent" />
      <p className="text-sm text-foreground-secondary">Loading...</p>
    </div>
  );
}

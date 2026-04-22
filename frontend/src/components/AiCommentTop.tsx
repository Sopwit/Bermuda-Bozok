import { Sparkles } from 'lucide-react';

type AiCommentTopProps = {
  advice: string;
};

export function AiCommentTop({ advice }: AiCommentTopProps) {
  return (
    <div className="card px-5 py-4 md:px-6 md:py-5">
      <div className="flex items-start gap-3">
        <div className="shrink-0 w-8 h-8 rounded-full bg-accent/10 border border-accent/30 flex items-center justify-center">
          <Sparkles className="w-4 h-4 text-accent" />
        </div>
        <div className="min-w-0">
          <div className="text-[11px] uppercase tracking-[0.18em] text-ink-muted font-semibold">
            AI Note
          </div>
          <p className="mt-1 font-display italic text-ink text-lg md:text-xl leading-snug">
            "{advice}"
          </p>
        </div>
      </div>
    </div>
  );
}

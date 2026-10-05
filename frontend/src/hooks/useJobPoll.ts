import { useEffect, useState } from "react";
import { api } from "../services/api";
import type { Job } from "../types";

export function useJobPoll(jobId: string | null, onDone?: (job: Job) => void) {
  const [job, setJob] = useState<Job | null>(null);
  useEffect(() => {
    if (!jobId) return;
    let stop = false;
    const tick = async () => {
      try {
        const j = await api<Job>(`/api/jobs/${jobId}`);
        if (stop) return;
        setJob(j);
        if (j.status === "completed" || j.status === "failed") {
          onDone?.(j);
          return;
        }
      } catch {
        /* keep polling */
      }
      if (!stop) window.setTimeout(tick, 800);
    };
    tick();
    return () => {
      stop = true;
    };
  }, [jobId]);
  return job;
}

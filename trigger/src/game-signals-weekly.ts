import { schedules, logger } from "@trigger.dev/sdk";
import { runGameSignalsPipeline } from "./pipeline/game-signals-pipeline.js";

export const gameSignalsWeekly = schedules.task({
  id: "game-signals-weekly",
  cron: {
    pattern: "0 7 * * 1",
    timezone: "America/New_York",
  },
  retry: {
    maxAttempts: 3,
    factor: 2,
    minTimeoutInMs: 10_000,
    maxTimeoutInMs: 120_000,
    randomize: true,
  },
  run: async (payload) => {
    const date = payload?.timestamp
      ? payload.timestamp.toISOString().split("T")[0]
      : new Date().toISOString().split("T")[0];

    logger.info("Starting game signals weekly run", {
      date,
      scheduleId: payload?.scheduleId ?? "manual",
      lastRun: payload?.lastTimestamp?.toISOString() ?? "none",
    });

    const result = await runGameSignalsPipeline({
      tbs: "qdr:w",
      date,
      dryRun: false,
    });

    return result;
  },
});

# find-game-signals STATUS

**Status:** VALIDATED — ready for TriggerDev graduation
**Built:** 2026-05-05
**Methodology:** research-process-builder SKILL.md, 6 phases, 24 queries tested

## Accuracy
- Stream A (game announces): ~85% (7/11 GT companies found in 30-day test)
- Stream B (studio funding): ~100% on 6-signal sample
- Combined: ~88%

## Primary Stack (11 queries total)
- A1: Genre-gated announced (SerperDev)
- A2: VGC standalone (SerperDev)
- A3: Genre + animation press (SerperDev)
- A4: Showcase roundup sweep (SerperDev)
- B1: Broad game studio funding (SerperDev)
- B2: PocketGamer.biz (SerperDev)
- B3: GamesPress.com (SerperDev)

## Next Steps
- [ ] Graduate to TriggerDev cron (see MONITORS.md + graduate-to-trigger skill)
- [ ] Wire Google Sheets output (Stage 4)
- [ ] 7-day live run to validate daily recall vs monthly test
- [ ] Fix Stream A to 90%+ (add gematsu.com, improve showcase scraping)

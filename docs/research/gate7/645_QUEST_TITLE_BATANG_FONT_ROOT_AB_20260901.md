# 645 — Quest title Batang font-root canary A/B

Date: 2026-09-01 KST

## Hypothesis

The client creates its UI fonts through `CreateFontA` with Hangul charset and
the face table `굴림체`, `굴림`, `돋움`, `바탕`. The current Wine root contained
`gulim.ttc` (Gulim/GulimChe/Dotum) but no `batang.ttc`, so a title-only face
fallback could have explained the visible split between upper title and lower
body.

## Candidate

- Immutable root `...acp949-xim25koreanlocale2-batangquestfont1.zip`.
- Adds only Windows `batang.ttc` (16,273,348 B; SHA-256
  `51d9a8d4205239c865e24b6eb7e6e6dbacfd59c3e2c46f623db0af45e169c9d8`)
  and `Batang`/`BatangChe` FontSubstitutes.
- Root ZIP SHA-256: `9a42c48e7d99c7af67df379ad173b4977df9f833b0f4b04e9b384dab74d049ac`.

## Actual result

- **VERIFIED:** canary reached character select and actual PatHouse quest panel
  through a server-list-issued account-bound browser session.
- **VERIFIED / REJECTED:** upper quest-list title remained corrupted while
  lower title/body stayed normal. Batang availability is not the fix.
- Production/default root remains unchanged.

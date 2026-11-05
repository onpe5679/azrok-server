# 183 Gate 2c CPU JIT feasibility and GPU probe (2026-07-20)

## VERIFIED

1. The web Emscripten makefile excludes `BOXEDWINE_JIT` and all native JIT
   target macros; `CPU::allocCPU()` always instantiates `NormalCPU`.
2. BoxedWine's existing native JIT creates executable host machine-code memory
   with AsmJit and jumps through `pfnJitCode`. It cannot become a WebAssembly
   JIT by enabling a build flag. The web source has no guest-block-to-new-Wasm
   function/table compiler.
3. The decoded-op cache already retains decoded x86 blocks. The measured cost
   is cached interpreter execution, not repeated decode.
4. No CheerpX runtime artifact exists in this workspace or the checked local
   tool locations. Its use therefore has no current executable baseline.
5. The host renderer now has an opt-in `?gpuprobe` WebGL2 elapsed-time-query
   measurement. It records only batched D3D work and reports a bounded
   `D3D9WEB_GPU_PROFILE` result; normal runs do not enable it.

## NOT VERIFIED

- GPU time for the actual PatHouse 23-FPS scene. This is the next required
  measurement before attributing the remaining 50-FPS gap solely to CPU.
- Whether a licensed/current CheerpX runtime can boot this Wine plus custom
  D3D9 bridge in this project. Public CheerpX material indicates a JIT x86
  engine, but its public WebVM 2.0 article describes 3D support as planned,
  not a proven path for this game.

## Consequence

Do not begin a speculative BoxedWine x86-to-Wasm block JIT yet. First collect
the GPU elapsed-time sample, then compare it with the already measured
worker/proxy time. If CPU remains dominant, CheerpX needs a real local
bootstrap gate before a multi-week in-tree JIT design is justified.

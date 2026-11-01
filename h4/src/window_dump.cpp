// Dev aid: H4_DUMP_WINDOWS=seconds logs the game's window tree once, that
// long after the first main loop pass (each window's RTTI class, rectangle
// in screen coordinates, mouse mode and visibility). Replaces the main loop
// pass (0x8D1360, `replace` in lifter.manifest when H4_WINDOW_DUMP=ON).

#include <chrono>
#include <cstdint>
#include <cstdlib>
#include <string>

#include "runtime/ctx.h"
#include "runtime/log.h"
#include "runtime/runtime.h"

namespace recomp::gen {

void f_008D1360_lifted(::recomp::Ctx& c);

namespace {

// The MSVC RTTI class name of a guest object's vtable.
std::string ClassName(uint32_t obj) {
  uint32_t vt = Rd32(obj);
  if (vt < 0x401000 || vt > 0xAD6000) return "?";
  uint32_t col = Rd32(vt - 4);
  if (col < 0x401000 || col > 0xAD6000) return "?";
  uint32_t td = Rd32(col + 12);
  return td ? GStr(td + 8) : "?";
}

void DumpTree(uint32_t w, int depth) {
  WarnF("h4: %*s%08X %s rect %d,%d-%d,%d mode %u vis %u\n", depth * 2, "", w,
        ClassName(w).c_str(), int(Rd32(w + 0x90)), int(Rd32(w + 0x94)), int(Rd32(w + 0x98)),
        int(Rd32(w + 0x9C)), Rd32(w + 8), GPtr(w + 0xA0)[0]);
  uint32_t head = Rd32(w + 0x34);
  if (!head || depth > 8) return;
  int i = 0;
  for (uint32_t node = Rd32(head); node != head && i < 400; node = Rd32(node), i++)
    DumpTree(Rd32(node + 8), depth + 1);
}

}  // namespace

void f_008D1360(::recomp::Ctx& c) {
  static const double at = [] {
    const char* e = Env("DUMP_WINDOWS");
    return e ? std::atof(e) : -1.0;
  }();
  static const auto t0 = std::chrono::steady_clock::now();
  static bool done = false;
  if (at >= 0 && !done &&
      std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count() >= at) {
    done = true;
    if (uint32_t top = Rd32(0xABACF4)) DumpTree(top, 0);
  }
  f_008D1360_lifted(c);
}

}  // namespace recomp::gen

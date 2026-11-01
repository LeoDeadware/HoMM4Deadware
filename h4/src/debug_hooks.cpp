// Dev-time instrumentation of lifted functions (replace entries in
// lifter.manifest marked "Dev").

#include <cstdint>
#include <mutex>
#include <set>
#include <string>

#include "runtime/ctx.h"
#include "runtime/log.h"
#include "runtime/runtime.h"

namespace recomp::gen {

void f_008D0F20_lifted(::recomp::Ctx& c);

// The modal message pump (dispatches with mouse clicks ignored): logs each
// new caller once.
void f_008D0F20(::recomp::Ctx& c) {
  static std::mutex mu;
  static std::set<uint32_t> seen;
  uint32_t ret = Rd32(c.esp);
  {
    std::lock_guard<std::mutex> l(mu);
    if (seen.insert(ret).second) WarnF("h4: modal pump from %08X\n", ret);
  }
  f_008D0F20_lifted(c);
}

}  // namespace recomp::gen

namespace recomp::gen {

void f_008D14E0_lifted(::recomp::Ctx& c);

// The main window procedure (hwnd, msg, wparam, lparam): logs mouse buttons
// with the modal-pump flag (0xAD2557) the procedure checks.
void f_008D14E0(::recomp::Ctx& c) {
  uint32_t msg = Rd32(c.esp + 8);
  static bool app_logged = false;
  if (!app_logged && Rd32(0xAD2528)) {
    app_logged = true;
    uint32_t app = Rd32(0xAD2528), vt = Rd32(app);
    WarnF("h4: app %08X vtable %08X idle %08X\n", app, vt, Rd32(vt + 4));
  }
  if (msg >= 0x201 && msg <= 0x203)
    WarnF("h4: wndproc msg %X lparam %08X modal %u paused %u\n", msg, Rd32(c.esp + 16), GPtr(0xAD2557)[0], GPtr(0xA87758)[0]);
  if (msg == 6) WarnF("h4: WM_ACTIVATE %X\n", Rd32(c.esp + 12));
  f_008D14E0_lifted(c);
}

}  // namespace recomp::gen

namespace recomp::gen {

void f_007212E0_lifted(::recomp::Ctx& c);

// The UI window under a screen point (x, y) -> window or 0: logs clicks'
// hit tests (one in 64 calls).
void f_007212E0(::recomp::Ctx& c) {
  static int n = 0;
  uint32_t x = Rd32(c.esp + 4), y = Rd32(c.esp + 8);
  f_007212E0_lifted(c);
  if (++n) {
    uint32_t w = c.eax, vt = w ? Rd32(w) : 0;
    WarnF("h4: window_at(%d, %d) -> %08X vtable %08X rect %d,%d mode %u\n", int(x), int(y), w,
          vt, w ? int(Rd32(w + 0x90)) : 0, w ? int(Rd32(w + 0x94)) : 0, w ? Rd32(w + 8) : 0);
    for (uint32_t p = w ? Rd32(w + 0x7C) : 0, i = 0; p && i < 6; p = Rd32(p + 0x7C), i++)
      WarnF("h4:   parent %08X vtable %08X\n", p, Rd32(p));
    // Once: the children of the hit window's parent (list at +0x34:
    // circular, node {next, prev, window}).
    static bool listed = false;
    uint32_t parent = w ? Rd32(w + 0x7C) : 0;
    if (parent && !listed && Rd32(parent) == 0x0098BABC) {
      listed = true;
      uint32_t head = Rd32(parent + 0x34);
      int i = 0;
      for (uint32_t node = Rd32(head); node != head && i < 200; node = Rd32(node), i++) {
        uint32_t ch = Rd32(node + 8);
        WarnF("h4:   child %08X vtable %08X rect %d,%d-%d,%d mode %u visible %u\n", ch, Rd32(ch),
              int(Rd32(ch + 0x90)), int(Rd32(ch + 0x94)), int(Rd32(ch + 0x98)),
              int(Rd32(ch + 0x9C)), Rd32(ch + 8), GPtr(ch + 0xA0)[0]);
      }
    }
  }
}

}  // namespace recomp::gen

namespace recomp::gen {

void f_00748970_lifted(::recomp::Ctx& c);

// The timer list (returns ms to the next timer, 10 when empty, 0 after
// running one): counts outcomes every 5000 calls.
void f_00748970(::recomp::Ctx& c) {
  static uint64_t calls = 0, ran = 0, empty = 0;
  f_00748970_lifted(c);
  calls++;
  if (c.eax == 0) ran++;
  if (c.eax == 10) empty++;
  if (calls % 200000 == 0) {
    WarnF("h4: timers: %llu calls, %llu ran, %llu empty, last wait %u\n",
          (unsigned long long)calls, (unsigned long long)ran, (unsigned long long)empty, c.eax);
    uint32_t mgr = Rd32(0xABDC98), head = mgr ? Rd32(mgr + 0xC) : 0;
    int i = 0;
    for (uint32_t node = head ? Rd32(head) : 0; node && node != head && i < 40;
         node = Rd32(node), i++) {
      uint32_t t = Rd32(node + 8);
      WarnF("h4:   timer %08X vtable %08X interval %d due %u\n", t, Rd32(t), int(Rd32(t + 4)),
            Rd32(t + 20));
    }
  }
}

}  // namespace recomp::gen

namespace recomp::gen {

void f_00590330_lifted(::recomp::Ctx& c);
void f_008D0C70_lifted(::recomp::Ctx& c);

uint64_t g_frames_set = 0, g_present_calls = 0, g_present_dirty = 0;

// An animated window's next frame (invalidates it).
void f_00590330(::recomp::Ctx& c) {
  g_frames_set++;
  f_00590330_lifted(c);
}

// The game's present: copies the dirty region to the screen when windows
// were invalidated (0xABACE0 counts them).
void f_008D0C70(::recomp::Ctx& c) {
  g_present_calls++;
  if (Rd32(0xABACE0)) g_present_dirty++;
  if (g_present_calls % 100000 == 0)
    WarnF("h4: present %llu calls, %llu dirty, %llu frames set\n",
          (unsigned long long)g_present_calls, (unsigned long long)g_present_dirty,
          (unsigned long long)g_frames_set);
  f_008D0C70_lifted(c);
}

}  // namespace recomp::gen

namespace recomp::gen {

void f_0071FD10_lifted(::recomp::Ctx& c);

// window->invalidate(rect*): logs the rect, the window's visible flag and
// position, and whether the dirty count (0xABACE0) grew (first 40 calls).
void f_0071FD10(::recomp::Ctx& c) {
  static int n = 0;
  uint32_t w = c.ecx, r = Rd32(c.esp + 4);
  uint32_t before = Rd32(0xABACE0);
  int l = int(Rd32(r)), t = int(Rd32(r + 4)), rr = int(Rd32(r + 8)), b = int(Rd32(r + 12));
  f_0071FD10_lifted(c);
  if (++n % 50 == 0)
    WarnF("h4: invalidate %08X vt %08X vis %u pos %d,%d rect %d,%d-%d,%d dirty %u->%u\n", w,
          Rd32(w), GPtr(w + 0xA0)[0], int(Rd32(w + 0x90)), int(Rd32(w + 0x94)), l, t, rr, b, before,
          Rd32(0xABACE0));
}

}  // namespace recomp::gen

namespace recomp::gen {

void f_005A0DD0_lifted(::recomp::Ctx& c);
void f_005A0EE0_lifted(::recomp::Ctx& c);

void LogMenuButton(const char* what, uint32_t b) {
  WarnF("h4: menu button %s %08X pressed %u disabled %u on_release %08X on_press %08X\n", what, b,
        GPtr(b + 0x138)[0], GPtr(b + 0xE4)[0], Rd32(b + 0xCC), Rd32(b + 0xD0));
}
void f_005A0DD0(::recomp::Ctx& c) {
  LogMenuButton("down", c.ecx);
  f_005A0DD0_lifted(c);
}
void f_005A0EE0(::recomp::Ctx& c) {
  LogMenuButton("up", c.ecx);
  f_005A0EE0_lifted(c);
}

}  // namespace recomp::gen

namespace recomp::gen {

void f_008E0001_lifted(::recomp::Ctx& c);

// _CxxThrowException(object, ThrowInfo*): logs the thrower, the first
// catchable type's name.
void f_008E0001(::recomp::Ctx& c) {
  uint32_t ret = Rd32(c.esp), obj = Rd32(c.esp + 4), info = Rd32(c.esp + 8);
  std::string type = "?";
  if (info) {
    uint32_t cta = Rd32(info + 12);
    if (cta && Rd32(cta)) {
      uint32_t ct = Rd32(cta + 4), td = Rd32(ct + 4);
      type = GStr(td + 8);
    }
  }
  WarnF("h4: C++ throw from %08X type %s object %08X\n", ret, type.c_str(), obj);
  f_008E0001_lifted(c);
}

}  // namespace recomp::gen

namespace recomp::gen {

void f_008E3C8D_lifted(::recomp::Ctx& c);

// CRT FindHandler(pExcept, pRN, pContext, pDC, pFuncInfo, recursive,
// CatchDepth, pMarkerRN): logs the frame registration it is given.
void f_008E3C8D(::recomp::Ctx& c) {
  uint32_t ret = Rd32(c.esp), exc = Rd32(c.esp + 4), rn = Rd32(c.esp + 8);
  WarnF("h4: FindHandler from %08X exc %08X code %08X rn %08X esp %08X fs0 %08X\n", ret, exc,
        exc ? Rd32(exc) : 0, rn, c.esp, Rd32(c.fs_base));
  WarnF("h4:   args pFuncInfo %08X recursive %u depth %u marker %08X\n", Rd32(c.esp + 20),
        Rd32(c.esp + 24) & 0xFF, Rd32(c.esp + 28), Rd32(c.esp + 32));
  uint32_t g = Rd32(c.fs_base);
  if (g != rn)
    WarnF("h4:   head %08X: %08X %08X %08X %08X %08X %08X\n", g, Rd32(g), Rd32(g + 4), Rd32(g + 8),
          Rd32(g + 12), Rd32(g + 16), Rd32(g + 20));
  f_008E3C8D_lifted(c);
}

}  // namespace recomp::gen

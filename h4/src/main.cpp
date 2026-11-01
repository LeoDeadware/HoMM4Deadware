// h4: Heroes of Might and Magic IV, natively.
//
//   h4 [--game-dir DIR] [-- GAME ARGS...]
//
// DIR is the game install (the folder with heroes4.exe, Data/, maps/).
// Defaults to $H4_GAME_DIR. Set H4_TRACE=1 to log every HLE call.

#include <sys/stat.h>

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>

#include "runtime/log.h"
#include "runtime/runtime.h"

int main(int argc, char** argv) {
  std::string game_dir, game_args;
  if (const char* e = std::getenv("H4_GAME_DIR")) game_dir = e;
  for (int i = 1; i < argc; i++) {
    if (!std::strcmp(argv[i], "--game-dir") && i + 1 < argc) {
      game_dir = argv[++i];
    } else if (!std::strcmp(argv[i], "--")) {
      for (i++; i < argc; i++) {
        if (!game_args.empty()) game_args += ' ';
        game_args += argv[i];
      }
    } else {
      std::fprintf(stderr, "usage: %s [--game-dir DIR] [-- GAME ARGS...]\n", argv[0]);
      return 2;
    }
  }
  if (game_dir.empty()) {
    std::fprintf(stderr, "h4: pass --game-dir or set H4_GAME_DIR\n");
    return 2;
  }
  while (game_dir.size() > 1 && game_dir.back() == '/') game_dir.pop_back();
  if (const char* t = std::getenv("H4_TRACE")) recomp::g_trace = *t && *t != '0';

  std::string exe = game_dir + "/heroes4.exe";
  struct stat st;
  if (stat(exe.c_str(), &st) != 0) {
    std::fprintf(stderr, "h4: %s not found\n", exe.c_str());
    return 2;
  }

  recomp::GameConfig game;
  game.id = "h4";
  game.guest_dir = "C:\\Heroes4";
  game.exe_name = "heroes4.exe";
  // What the retail installer writes (the GOG install writes nothing).
  const std::string key = "HKLM\\SOFTWARE\\New World Computing\\Heroes of Might and Magic IV\\1.0";
  // The game's own settings key: without a "resolution" (the screen width)
  // it takes the desktop's size, which its interface does not support past
  // 1280x1024. 1024 is its 1024x768 mode.
  const std::string settings = "HKCU\\Software\\New World Computing\\Heroes of Might and Magic IV";
  game.registry = {{key, "AppPath", game.guest_dir},
                   {settings, "resolution", "1024", 4}};
  // The game draws its own cursor where GetCursorPos says, in exclusive
  // mode too, and never re-centres it.
  game.own_cursor = true;
  return recomp::RunProcess(game, exe, game_dir, game_args);
}

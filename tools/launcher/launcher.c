// Heroes IV.app's CFBundleExecutable (built by tools/install_app.sh; kit rule R-I5, owner 2026-11-06).
// A bash script as the bundle's executable cannot read the app's files when the app is opened from
// Finder under ~/Desktop (macOS privacy, TCC: the responsible process is the interpreter). This small
// Mach-O sets the environment, then execv()s the game in the same process:
//   - player files in H4_PLAYER_ROOT (baked at install, test installs only), else
//     ~/Library/Application Support/Heroes IV/player: XDG_DATA_HOME=<root>/data (the runtime keeps
//     registry.txt, saves under install/games, crashes/ and hangs/ in <root>/data/h4), the log
//     <root>/logs/h4.log (stdout + stderr; every start rotates it to h4.log.1 .. .5);
//   - the language: $H4_LANG, else <root>/settings.toml [launcher] language, else en (owner
//     2026-11-06: English by default, the player's choice remembered). en plays Resources/game
//     (the original data), uk Resources/game-uk (the Ukrainian patch; The Gathering Storm stays
//     English). Saves are shared: both read the same <root>/data/h4;
//   - the launcher window (osascript dialog): English / Українська / Quit, the saved choice as the
//     default button; skipped in test runs (H4_BACKGROUND, H4_NO_UI) and with H4_LAUNCHER=0;
//   - screen defaults: H4_RESOLUTION=wide, H4_FILTER=fsr, H4_DEBAND=1, H4_SHARPNESS=0.2,
//     H4_WINGS_DIR=Resources/wings.
//   - the DMG installer (tools/make_dmg.sh: no game code, no game data in the bundle): the first run
//     finds the player's GOG installer (H4_SETUP, else ~/Downloads/setup_heroes_of_might_and_magic_4_
//     complete*.exe, else a file dialog), copies this bundle to ~/Desktop/Heroes IV.app (H4_INSTALL_APP)
//     and runs Resources/build/install_game.sh there (unpack, lift, compile with Command Line Tools,
//     the Ukrainian version) with a progress window; the game data then lives next to the player
//     folder: <root>/../game and <root>/../game-uk.
// Every variable already in the environment wins (open --env, tests).
#include <errno.h>
#include <fcntl.h>
#include <libgen.h>
#include <limits.h>
#include <mach-o/dyld.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>

#ifndef H4_PLAYER_ROOT
#define H4_PLAYER_ROOT ""
#endif

static void mkdirs(const char* path) {
  char p[PATH_MAX];
  snprintf(p, sizeof p, "%s", path);
  for (char* s = p + 1; *s; s++)
    if (*s == '/') {
      *s = 0;
      mkdir(p, 0755);
      *s = '/';
    }
  mkdir(p, 0755);
}

static void setdef(const char* k, const char* v) { setenv(k, v, 0); }

// settings.toml [launcher] <key> = "value"; 0 if absent.
static int read_setting(const char* file, const char* key, char* out, size_t n) {
  FILE* f = fopen(file, "r");
  if (!f) return 0;
  char line[512];
  int in = 0, found = 0;
  size_t kl = strlen(key);
  while (fgets(line, sizeof line, f)) {
    char* s = line;
    while (*s == ' ' || *s == '\t') s++;
    if (*s == '[') {
      in = strncmp(s, "[launcher]", 10) == 0;
      continue;
    }
    if (!in || strncmp(s, key, kl) || (s[kl] != ' ' && s[kl] != '=')) continue;
    char* v = strchr(s, '=');
    if (!v) continue;
    v++;
    while (*v == ' ' || *v == '"') v++;
    size_t i = 0;
    while (v[i] && v[i] != '"' && v[i] != ' ' && v[i] != '#' && v[i] != '\n' && i + 1 < n) out[i] = v[i], i++;
    out[i] = 0;
    found = 1;
  }
  fclose(f);
  return found;
}

static void write_language(const char* file, const char* lang) {
  FILE* f = fopen(file, "w");
  if (!f) return;
  fprintf(f, "[launcher]\nlanguage = \"%s\"\n", lang);
  fclose(f);
}

// The launcher window: returns "en", "uk" or "quit" (the saved language if no answer).
static void ask_language(char* lang, size_t n) {
  int uk = strcmp(lang, "uk") == 0;
  char cmd[1024], ans[64] = "";
  snprintf(cmd, sizeof cmd,
           "/usr/bin/osascript -e 'button returned of (display dialog \"%s\" with title \"Heroes of Might "
           "and Magic IV\" buttons {\"%s\", \"English\", \"Українська\"} default button \"%s\")' 2>/dev/null",
           uk ? "Мова гри:" : "Game language:", uk ? "Вийти" : "Quit", uk ? "Українська" : "English");
  FILE* p = popen(cmd, "r");
  if (p) {
    if (!fgets(ans, sizeof ans, p)) ans[0] = 0;
    pclose(p);
  }
  ans[strcspn(ans, "\n")] = 0;
  printf("launcher: window -> %s\n", *ans ? ans : "(no answer)");
  if (strcmp(ans, "English") == 0) snprintf(lang, n, "en");
  else if (strcmp(ans, "Українська") == 0) snprintf(lang, n, "uk");
  else if (*ans) snprintf(lang, n, "quit");  // Quit / Вийти
}

static int ui_uk = 0;
#define TR(en, uk) (ui_uk ? (uk) : (en))

static void alert(const char* msg) {
  printf("launcher: alert: %s\n", msg);
  fflush(stdout);
  if (getenv("H4_NO_UI")) return;
  char cmd[1024];
  snprintf(cmd, sizeof cmd, "/usr/bin/osascript -e 'display alert \"Heroes IV\" message \"%s\"' >/dev/null 2>&1", msg);
  system(cmd);
}

// The GOG installer: H4_SETUP, the newest in ~/Downloads, else the player picks it.
static int find_setup(const char* home, char* out, size_t n) {
  char cmd[PATH_MAX * 2];
  out[0] = 0;
  if (getenv("H4_SETUP")) snprintf(out, n, "%s", getenv("H4_SETUP"));
  if (!*out) {
    snprintf(cmd, sizeof cmd, "/bin/ls -t '%s'/Downloads/setup_heroes_of_might_and_magic_4_complete*.exe 2>/dev/null", home);
    FILE* p = popen(cmd, "r");
    if (p) { if (!fgets(out, (int)n, p)) out[0] = 0; pclose(p); }
    out[strcspn(out, "\n")] = 0;
  }
  if (!*out && !getenv("H4_NO_UI")) {
    snprintf(cmd, sizeof cmd, "/usr/bin/osascript -e 'POSIX path of (choose file with prompt \"%s\")' 2>/dev/null",
             TR("Choose the GOG installer of Heroes of Might and Magic IV Complete (setup_heroes_of_might_and_magic_4_complete_....exe)",
                "Оберіть інсталятор GOG Heroes of Might and Magic IV Complete (setup_heroes_of_might_and_magic_4_complete_....exe)"));
    FILE* p = popen(cmd, "r");
    if (p) { if (!fgets(out, (int)n, p)) out[0] = 0; pclose(p); }
    out[strcspn(out, "\n")] = 0;
  }
  return *out ? 0 : 1;
}

// First run of the DMG installer: this bundle -> target, then the game is built there.
static int install_game(const char* here, const char* sup, const char* target, const char* setup) {
  char cmd[PATH_MAX * 6], prog[PATH_MAX];
  snprintf(cmd, sizeof cmd, "/bin/rm -rf '%s' && /usr/bin/ditto '%s/../..' '%s'", target, here, target);
  if (system(cmd) != 0) { alert(TR("Could not create Heroes IV.app.", "Не вдалося створити Heroes IV.app.")); return 1; }
  mkdirs(sup);
  snprintf(prog, sizeof prog, "%s/install-progress.txt", sup);
  unlink(prog);
  if (!getenv("H4_NO_UI")) {
    snprintf(cmd, sizeof cmd, "/usr/bin/osascript -l JavaScript '%s/../Resources/build/progress.js' '%s' >/dev/null 2>&1 &", here, prog);
    system(cmd);
  }
  printf("launcher: installing the game from %s -> %s\n", setup, target);
  fflush(stdout);
  snprintf(cmd, sizeof cmd, "/bin/bash '%s/Contents/Resources/build/install_game.sh' '%s/Contents/Resources/build' '%s' "
           "'%s/Contents/MacOS/h4-bin' '%s' '%s'", target, target, sup, target, setup, prog);
  if (system(cmd) != 0) {
    char msg[512] = "", line[512];
    FILE* f = fopen(prog, "r");
    while (f && fgets(line, sizeof line, f)) snprintf(msg, sizeof msg, "%s", line);
    if (f) fclose(f);
    msg[strcspn(msg, "\n\"'")] = 0;
    char a[700];
    snprintf(a, sizeof a, TR("Installation failed: %s", "Гру не встановлено: %s"), *msg ? msg : "?");
    alert(a);
    return 1;
  }
  snprintf(cmd, sizeof cmd, "/bin/rm -rf '%s/Contents/Resources/build' && /usr/bin/codesign --force --deep -s - '%s' >/dev/null 2>&1",
           target, target);
  system(cmd);
  return 0;
}

int main(int argc, char** argv) {
  char exe[PATH_MAX], real[PATH_MAX];
  uint32_t sz = sizeof exe;
  if (_NSGetExecutablePath(exe, &sz) != 0 || !realpath(exe, real)) return 70;
  char here[PATH_MAX];
  snprintf(here, sizeof here, "%s", dirname(real));  // .../Heroes IV.app/Contents/MacOS
  const char* h = getenv("HOME");

  char root[PATH_MAX] = H4_PLAYER_ROOT, parent[PATH_MAX];
  if (getenv("H4_PLAYER_ROOT")) snprintf(root, sizeof root, "%s", getenv("H4_PLAYER_ROOT"));
  struct stat st;
  snprintf(parent, sizeof parent, "%s", root);
  if (!*root || stat(dirname(parent), &st) != 0)  // baked folder gone (another Mac): user library
    snprintf(root, sizeof root, "%s/Library/Application Support/Heroes IV/player", h ? h : "/tmp");
  // Under ~/Desktop macOS privacy (TCC) may refuse the baked folder: then the user library.
  char data[PATH_MAX], logs[PATH_MAX], log[PATH_MAX];
  int fd = -1, denied = 0;
  for (int attempt = 0; attempt < 2 && fd < 0; attempt++) {
    if (attempt) {
      denied = errno;
      snprintf(root, sizeof root, "%s/Library/Application Support/Heroes IV/player", h ? h : "/tmp");
    }
    snprintf(data, sizeof data, "%s/data", root);
    snprintf(logs, sizeof logs, "%s/logs", root);
    mkdirs(data);
    mkdirs(logs);
    snprintf(log, sizeof log, "%s/h4.log", logs);
    // Every start rotates h4.log -> h4.log.1 .. .5 (the oldest is dropped): a crashed run's log
    // survives the next start (PIT-never-kill-running-game; HP2 lost its evidence that way).
    if (stat(log, &st) == 0) {
      char a[PATH_MAX], b[PATH_MAX];
      for (int i = 5; i > 1; i--) {
        snprintf(a, sizeof a, "%s.%d", log, i - 1);
        snprintf(b, sizeof b, "%s.%d", log, i);
        rename(a, b);
      }
      snprintf(a, sizeof a, "%s.1", log);
      rename(log, a);
    }
    fd = open(log, O_WRONLY | O_CREAT | O_APPEND, 0644);
  }
  setdef("XDG_DATA_HOME", data);
  if (fd >= 0) {
    time_t t = time(NULL);
    dprintf(fd, "=== %s", ctime(&t));
    dprintf(fd, "launcher: %s, player files %s\n", real, root);
    if (denied) dprintf(fd, "launcher: baked player folder refused (%s): user library used\n", strerror(denied));
    dup2(fd, 1);
    dup2(fd, 2);
    close(fd);
  }

  char settings[PATH_MAX], lang[16] = "en";
  snprintf(settings, sizeof settings, "%s/settings.toml", root);
  int env_lang = getenv("H4_LANG") && *getenv("H4_LANG");
  if (env_lang) snprintf(lang, sizeof lang, "%s", getenv("H4_LANG"));
  else read_setting(settings, "language", lang, sizeof lang);
  if (strcmp(lang, "uk") != 0) snprintf(lang, sizeof lang, "en");
  const char* lw = getenv("H4_LAUNCHER");
  if (!env_lang && !getenv("H4_NO_UI") && !getenv("H4_BACKGROUND") && !(lw && strcmp(lw, "0") == 0)) {
    char was[16];
    snprintf(was, sizeof was, "%s", lang);
    ask_language(lang, sizeof lang);
    if (strcmp(lang, "quit") == 0) return 0;
    if (strcmp(was, lang) != 0 || stat(settings, &st) != 0) write_language(settings, lang);
  }
  setenv("H4_LANG", lang, 1);
  ui_uk = strcmp(lang, "uk") == 0;
  setenv("H4_UI_LANG", lang, 1);

  // The DMG installer: no game code in this bundle -> install into the target app, then run it.
  char bin[PATH_MAX], kit[PATH_MAX], sup[PATH_MAX];
  snprintf(parent, sizeof parent, "%s", root);
  snprintf(sup, sizeof sup, "%s", dirname(parent));  // the game data lives next to the player folder
  snprintf(bin, sizeof bin, "%s/h4-bin", here);
  snprintf(kit, sizeof kit, "%s/../Resources/build/install_game.sh", here);
  if (stat(bin, &st) != 0 && stat(kit, &st) == 0) {
    char target[PATH_MAX], tbin[PATH_MAX], setup[PATH_MAX];
    if (getenv("H4_INSTALL_APP")) snprintf(target, sizeof target, "%s", getenv("H4_INSTALL_APP"));
    else snprintf(target, sizeof target, "%s/Desktop/Heroes IV.app", h ? h : "/tmp");
    snprintf(tbin, sizeof tbin, "%s/Contents/MacOS/h4-bin", target);
    if (stat(tbin, &st) != 0) {
      if (find_setup(h ? h : "/tmp", setup, sizeof setup) != 0) return 72;
      if (install_game(here, sup, target, setup) != 0) return 73;
    }
    snprintf(tbin, sizeof tbin, "%s/Contents/MacOS/heroes4", target);
    fflush(stdout);
    argv[0] = tbin;
    execv(tbin, argv);
    return 71;
  }

  char game[PATH_MAX], wings[PATH_MAX];
  const char* gd = strcmp(lang, "uk") == 0 ? "game-uk" : "game";
  snprintf(game, sizeof game, "%s/../Resources/%s", here, gd);
  if (stat(game, &st) != 0) snprintf(game, sizeof game, "%s/%s", sup, gd);  // installed from the DMG
  if (stat(game, &st) != 0) snprintf(game, sizeof game, "%s/../Resources/game", here);
  snprintf(wings, sizeof wings, "%s/../Resources/wings", here);
  setdef("H4_RESOLUTION", "wide");
  setdef("H4_FILTER", "fsr");
  setdef("H4_DEBAND", "1");
  setdef("H4_SHARPNESS", "0.2");
  setdef("H4_WINGS_DIR", wings);
  printf("launcher: language %s, game %s\n", lang, game);
  fflush(stdout);

  char* args[argc + 4];
  int k = 0;
  args[k++] = bin;
  args[k++] = "--game-dir";
  args[k++] = game;
  for (int i = 1; i < argc; i++)
    if (strncmp(argv[i], "-psn_", 5) != 0) args[k++] = argv[i];  // old Finder process-serial argument
  args[k] = NULL;
  execv(bin, args);
  fprintf(stderr, "launcher: cannot start %s: %s\n", bin, strerror(errno));
  return 71;
}

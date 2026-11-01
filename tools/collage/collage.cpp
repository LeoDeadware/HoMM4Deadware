// Bosch-style triptych wings from Heroes IV sprites.
//   collage DIR WING OUT.bmp WIDTH HEIGHT SEED GRASS.bmp
// WING: paradise or hell (the main menu's), or FACTION_light / FACTION_dark
// (life, order, nature, death, chaos, might: the combat wings).
// DIR holds .rgba files (u32 w, u32 h, RGBA): c_* creatures, h_* heroes,
// o_* map objects (o_castle* are landmarks).
#include <dirent.h>

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <random>
#include <string>
#include <vector>

struct Sprite {
  std::string name;
  int w = 0, h = 0;
  std::vector<float> px;  // premultiplied RGBA, 0..1
};

struct Canvas {
  int w, h;
  std::vector<float> c;  // RGB 0..1
  float* at(int x, int y) { return &c[(size_t(y) * w + x) * 3]; }
};

static bool Load(const std::string& path, Sprite* s) {
  FILE* f = std::fopen(path.c_str(), "rb");
  if (!f) return false;
  uint32_t wh[2];
  if (std::fread(wh, 4, 2, f) != 2) return false;
  s->w = int(wh[0]);
  s->h = int(wh[1]);
  std::vector<uint8_t> raw(size_t(s->w) * s->h * 4);
  if (std::fread(raw.data(), 1, raw.size(), f) != raw.size()) return false;
  std::fclose(f);
  s->px.resize(raw.size());
  for (size_t i = 0; i < raw.size(); i += 4) {
    float a = raw[i + 3] / 255.0f;
    for (int k = 0; k < 3; k++) s->px[i + k] = raw[i + k] / 255.0f * a;
    s->px[i + 3] = a;
  }
  return true;
}

// Editor placeholders in the archives: big flat single-colour boxes with a
// label ("DELETE ME NOW!!!", "Dwelling", "Shrine 1").
static bool Placeholder(const Sprite& s) {
  if (s.w == 613 && s.h == 513) return true;
  std::vector<std::pair<uint32_t, int>> hist;
  int opaque = 0;
  std::vector<int> counts(1 << 15, 0);
  for (size_t i = 0; i < s.px.size(); i += 4) {
    float a = s.px[i + 3];
    if (a < 0.9f) continue;
    opaque++;
    int r = int(s.px[i] / a * 31), g = int(s.px[i + 1] / a * 31), b = int(s.px[i + 2] / a * 31);
    counts[(r << 10) | (g << 5) | b]++;
  }
  if (opaque < 50) return true;
  int top = *std::max_element(counts.begin(), counts.end());
  return top > opaque / 5;
}

// Premultiplied bilinear sample, 0 outside.
static void Sample(const Sprite& s, float x, float y, float* o) {
  x -= 0.5f;
  y -= 0.5f;
  int x0 = int(std::floor(x)), y0 = int(std::floor(y));
  float fx = x - x0, fy = y - y0;
  o[0] = o[1] = o[2] = o[3] = 0;
  for (int j = 0; j < 2; j++)
    for (int i = 0; i < 2; i++) {
      int xx = x0 + i, yy = y0 + j;
      if (xx < 0 || yy < 0 || xx >= s.w || yy >= s.h) continue;
      float w = (i ? fx : 1 - fx) * (j ? fy : 1 - fy);
      const float* p = &s.px[(size_t(yy) * s.w + xx) * 4];
      for (int k = 0; k < 4; k++) o[k] += p[k] * w;
    }
}

struct Grade {
  float tint[3];   // multiplied in
  float sat;       // 1 = unchanged
  float bright;
};

// Draws s scaled by k with its bottom-centre at (cx, by), graded and
// optionally flipped; when silhouette > 0 the sprite is darkened towards a
// silhouette with an orange rim (hell's burning city).
static void Draw(Canvas& cv, const Sprite& s, float cx, float by, float k, bool flip, const Grade& g,
                 float silhouette = 0) {
  int dw = std::max(1, int(s.w * k)), dh = std::max(1, int(s.h * k));
  int x0 = int(cx - dw / 2.0f), y0 = int(by - dh);
  // Box-filtered when shrinking a lot: average several bilinear samples.
  int ss = k < 0.5f ? 3 : k < 0.8f ? 2 : 1;
  for (int y = std::max(0, y0); y < std::min(cv.h, y0 + dh); y++)
    for (int x = std::max(0, x0); x < std::min(cv.w, x0 + dw); x++) {
      float acc[4] = {0, 0, 0, 0};
      for (int sy = 0; sy < ss; sy++)
        for (int sx = 0; sx < ss; sx++) {
          float u = (x - x0 + (sx + 0.5f) / ss) / k, v = (y - y0 + (sy + 0.5f) / ss) / k;
          if (flip) u = s.w - u;
          float o[4];
          Sample(s, u, v, o);
          for (int q = 0; q < 4; q++) acc[q] += o[q];
        }
      for (int q = 0; q < 4; q++) acc[q] /= float(ss * ss);
      float a = acc[3];
      if (a <= 0.002f) continue;
      float col[3] = {acc[0] / a, acc[1] / a, acc[2] / a};
      float l = 0.3f * col[0] + 0.59f * col[1] + 0.11f * col[2];
      for (int q = 0; q < 3; q++) {
        float c = l + (col[q] - l) * g.sat;
        c *= g.tint[q] * g.bright;
        if (silhouette > 0) c = c * (1 - silhouette) + silhouette * (q == 0 ? 0.10f : q == 1 ? 0.05f : 0.03f);
        col[q] = c;
      }
      float* d = cv.at(x, y);
      for (int q = 0; q < 3; q++) d[q] = d[q] * (1 - a) + std::clamp(col[q], 0.0f, 1.0f) * a;
    }
}

static float Noise(int x, int y, int seed) {
  uint32_t h = uint32_t(x) * 374761393u + uint32_t(y) * 668265263u + uint32_t(seed) * 2147483647u;
  h = (h ^ (h >> 13)) * 1274126177u;
  return ((h ^ (h >> 16)) & 0xFFFF) / 65535.0f;
}
// Smooth value noise.
static float VNoise(float x, float y, int seed) {
  int xi = int(std::floor(x)), yi = int(std::floor(y));
  float fx = x - xi, fy = y - yi;
  fx = fx * fx * (3 - 2 * fx);
  fy = fy * fy * (3 - 2 * fy);
  float a = Noise(xi, yi, seed), b = Noise(xi + 1, yi, seed), c = Noise(xi, yi + 1, seed),
        d = Noise(xi + 1, yi + 1, seed);
  return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy;
}
static float Fbm(float x, float y, int seed) {
  float s = 0, a = 0.5f;
  for (int o = 0; o < 5; o++) {
    s += a * VNoise(x, y, seed + o * 17);
    x *= 2.03f;
    y *= 2.03f;
    a *= 0.5f;
  }
  return s;
}

static void Mix(float* d, const float* c, float t) {
  for (int q = 0; q < 3; q++) d[q] = d[q] * (1 - t) + c[q] * t;
}

// A ground texture (24-bit BMP), sampled mirrored so it tiles seamlessly.
struct Tex {
  int w = 0, h = 0;
  std::vector<float> c;
  float mean[3] = {0, 0, 0};
  bool Load(const char* path) {
    FILE* f = std::fopen(path, "rb");
    if (!f) return false;
    uint8_t hd[54];
    if (std::fread(hd, 1, 54, f) != 54) return false;
    int32_t ww, hh;
    uint32_t off;
    std::memcpy(&off, hd + 10, 4);
    std::memcpy(&ww, hd + 18, 4);
    std::memcpy(&hh, hd + 22, 4);
    w = ww;
    h = std::abs(hh);
    c.resize(size_t(w) * h * 3);
    std::fseek(f, off, SEEK_SET);
    int row = (w * 3 + 3) & ~3;
    std::vector<uint8_t> l(row);
    for (int y = 0; y < h; y++) {
      if (std::fread(l.data(), 1, row, f) != size_t(row)) return false;
      int yy = hh < 0 ? y : h - 1 - y;
      for (int x = 0; x < w; x++)
        for (int q = 0; q < 3; q++) c[(size_t(yy) * w + x) * 3 + q] = l[3 * x + 2 - q] / 255.0f;
    }
    std::fclose(f);
    for (size_t i = 0; i < c.size(); i++) mean[i % 3] += c[i] / (w * h);
    return true;
  }
  const float* at(int x, int y) const {
    x = std::abs(x) % (2 * w);
    y = std::abs(y) % (2 * h);
    if (x >= w) x = 2 * w - 1 - x;
    if (y >= h) y = 2 * h - 1 - y;
    return &c[(size_t(y) * w + x) * 3];
  }
};

// A wing's look: the light one is Eden's (sky, meadow, pond, processions),
// the dark one hell's (fire on the horizon, scorched ground, frozen lake, a
// giant); the faction picks who populates it and the colours.
struct Theme {
  const char* name;
  std::vector<const char*> flyers;
  const char *ring, *monks, *proc_a, *proc_b;  // light: the processions
  std::vector<const char*> animals;            // light: round the pond; dark: the crowds
  const char *hero, *big;                      // the foreground
  const char *giant, *lake_a, *lake_b, *line_a, *line_b;  // dark
  float sky_top[3], sky_low[3], meadow[3], water[3];      // light
  float glow[3], ground_a[3], ground_b[3], ice[3];        // dark
  Grade light, dark;
};

const Theme kThemes[] = {
    {"life", {"archangel", "griffin"}, "peasant", "monk", "crusader", "champion",
     {"griffin", "squire", "pikeman", "monk"}, "life", "archangel",
     "archangel", "pikeman", "squire", "peasant", "monk",
     {0.55f, 0.68f, 0.78f}, {0.88f, 0.90f, 0.84f}, {1.0f, 1.0f, 1.0f}, {0.42f, 0.60f, 0.70f},
     {0.85f, 0.65f, 0.25f}, {0.30f, 0.22f, 0.10f}, {0.10f, 0.08f, 0.06f}, {0.45f, 0.50f, 0.55f},
     {{1.02f, 1.0f, 0.90f}, 0.85f, 1.02f}, {{1.05f, 0.95f, 0.80f}, 0.85f, 0.85f}},
    {"order", {"genie", "gargoyle", "dragon_golem"}, "halfling", "mage", "dwarf", "gold_golem",
     {"naga", "gargoyle", "halfling", "dwarf"}, "order", "titan",
     "dragon_golem", "gold_golem", "dwarf", "halfling", "mage",
     {0.50f, 0.62f, 0.85f}, {0.86f, 0.90f, 0.95f}, {0.92f, 0.98f, 1.08f}, {0.45f, 0.58f, 0.80f},
     {0.35f, 0.40f, 0.85f}, {0.14f, 0.15f, 0.28f}, {0.06f, 0.06f, 0.10f}, {0.42f, 0.48f, 0.62f},
     {{0.95f, 0.98f, 1.06f}, 0.85f, 1.02f}, {{0.85f, 0.90f, 1.10f}, 0.80f, 0.82f}},
    {"nature", {"phoenix", "faerie_dragon", "sprite", "griffin"}, "leprechaun", "elf", "elf", "satyr",
     {"unicorn", "white_tiger", "wolf", "griffin"}, "nature", "faerie_dragon",
     "faerie_dragon", "waspwort", "sprite", "satyr", "elf",
     {0.62f, 0.72f, 0.70f}, {0.93f, 0.90f, 0.72f}, {0.92f, 1.08f, 0.88f}, {0.38f, 0.62f, 0.60f},
     {0.30f, 0.75f, 0.60f}, {0.10f, 0.22f, 0.14f}, {0.04f, 0.08f, 0.05f}, {0.35f, 0.50f, 0.48f},
     {{0.98f, 1.04f, 0.90f}, 0.95f, 1.0f}, {{0.85f, 1.05f, 0.90f}, 0.85f, 0.80f}},
    {"death", {"ghost", "bone_dragon", "venom_spawn", "vampire"}, "skeleton", "mummy", "skeleton", "vampire",
     {"imp", "cerberus", "venom", "ghost"}, "death", "archdevil",
     "bone_dragon", "skeleton", "zombie", "zombie", "mummy",
     {0.60f, 0.62f, 0.66f}, {0.82f, 0.82f, 0.80f}, {0.85f, 0.88f, 0.85f}, {0.45f, 0.52f, 0.55f},
     {0.75f, 0.28f, 0.06f}, {0.30f, 0.12f, 0.05f}, {0.11f, 0.07f, 0.06f}, {0.40f, 0.48f, 0.55f},
     {{0.95f, 0.95f, 0.95f}, 0.70f, 0.95f}, {{1.05f, 0.82f, 0.70f}, 0.85f, 0.80f}},
    {"chaos", {"black_dragon", "efreet", "beholder", "nightmare"}, "bandit", "troglodyte", "orc", "minotaur",
     {"medusa", "nightmare", "orc", "troglodyte"}, "chaos", "black_dragon",
     "hydra", "troglodyte", "bandit", "orc", "minotaur",
     {0.58f, 0.48f, 0.70f}, {0.92f, 0.80f, 0.82f}, {1.05f, 0.92f, 1.02f}, {0.50f, 0.45f, 0.68f},
     {0.70f, 0.18f, 0.45f}, {0.25f, 0.08f, 0.18f}, {0.08f, 0.04f, 0.08f}, {0.42f, 0.38f, 0.55f},
     {{1.04f, 0.94f, 1.02f}, 0.90f, 1.0f}, {{1.08f, 0.80f, 0.95f}, 0.85f, 0.80f}},
    {"might", {"thunderbird", "harpy"}, "nomad", "ogre_mage", "berserker", "centaur",
     {"behemoth", "cyclops", "troll", "wolf"}, "might", "behemoth",
     "cyclops", "berserker", "nomad", "troll", "centaur",
     {0.70f, 0.66f, 0.58f}, {0.95f, 0.86f, 0.66f}, {1.12f, 1.0f, 0.72f}, {0.50f, 0.58f, 0.60f},
     {0.85f, 0.42f, 0.12f}, {0.32f, 0.18f, 0.08f}, {0.12f, 0.08f, 0.05f}, {0.48f, 0.46f, 0.44f},
     {{1.06f, 1.0f, 0.85f}, 0.90f, 1.02f}, {{1.08f, 0.88f, 0.70f}, 0.85f, 0.82f}},
};

int main(int argc, char** argv) {
  if (argc < 8) return 2;
  Tex tex;
  if (!tex.Load(argv[7])) return 3;
  std::string dir = argv[1], wing = argv[2];
  // paradise and hell: the main menu's wings, life's light one and the
  // original hell (death's dark one).
  const bool hell = wing == "hell" || wing.size() > 5 && wing.substr(wing.size() - 5) == "_dark";
  const std::string faction = wing == "paradise" ? "life" : wing == "hell" ? "death" : wing.substr(0, wing.find('_'));
  const Theme* thp = nullptr;
  for (const Theme& t : kThemes)
    if (faction == t.name) thp = &t;
  if (!thp) return 4;
  const Theme& th = *thp;
  Canvas cv{std::atoi(argv[4]), std::atoi(argv[5]), {}};
  const int seed = std::atoi(argv[6]);
  cv.c.assign(size_t(cv.w) * cv.h * 3, 0);
  std::mt19937 rng(seed);
  auto U = [&](float a, float b) { return std::uniform_real_distribution<float>(a, b)(rng); };

  std::vector<Sprite> crea, hero, obj, castle;
  if (DIR* d = opendir(dir.c_str())) {
    while (dirent* e = readdir(d)) {
      std::string n = e->d_name;
      if (n.size() < 6 || n.substr(n.size() - 5) != ".rgba") continue;
      Sprite s;
      s.name = n;
      if (!Load(dir + "/" + n, &s)) continue;
      if (Placeholder(s)) continue;
      if (n.rfind("c_", 0) == 0) crea.push_back(std::move(s));
      else if (n.rfind("h_", 0) == 0) hero.push_back(std::move(s));
      else if (n.rfind("o_castle", 0) == 0) castle.push_back(std::move(s));
      else obj.push_back(std::move(s));
    }
    closedir(d);
  }
  std::sort(crea.begin(), crea.end(), [](auto& a, auto& b) { return a.name < b.name; });
  std::sort(obj.begin(), obj.end(), [](auto& a, auto& b) { return a.name < b.name; });
  std::sort(castle.begin(), castle.end(), [](auto& a, auto& b) { return a.name < b.name; });
  std::sort(hero.begin(), hero.end(), [](auto& a, auto& b) { return a.name < b.name; });
  auto flyer = [&](const std::string& n) {
    for (const char* f : th.flyers)
      if (n.find(f) != std::string::npos) return true;
    return false;
  };
  std::vector<int> flyers, walkers;
  for (int i = 0; i < int(crea.size()); i++) (flyer(crea[i].name) ? flyers : walkers).push_back(i);

  const int W = cv.w, H = cv.h;
  const float horizon = H * (hell ? 0.30f : 0.24f);

  // ---- background
  for (int y = 0; y < H; y++)
    for (int x = 0; x < W; x++) {
      float* p = cv.at(x, y);
      float t = float(y) / H;
      float n = Fbm(x * 0.012f, y * 0.012f, seed);
      if (!hell) {
        if (y < horizon) {  // pale Eden sky, lighter at the horizon
          float s = float(y) / horizon;
          for (int q = 0; q < 3; q++) p[q] = th.sky_top[q] * (1 - s) + th.sky_low[q] * s;
          float cl[3] = {0.97f, 0.97f, 0.93f};
          Mix(p, cl, std::clamp((Fbm(x * 0.008f, y * 0.02f, seed + 5) - 0.55f) * 2.5f, 0.0f, 0.6f));
        } else {  // meadow: from blue-green distance to rich green foreground
          float s = (y - horizon) / (H - horizon);
          float far[3] = {0.52f, 0.62f, 0.55f}, mid[3] = {0.40f, 0.55f, 0.28f}, nearc[3] = {0.30f, 0.42f, 0.18f};
          for (int q = 0; q < 3; q++)
            p[q] = th.meadow[q] *
                   (s < 0.3f ? far[q] + (mid[q] - far[q]) * (s / 0.3f) : mid[q] + (nearc[q] - mid[q]) * ((s - 0.3f) / 0.7f));
          // The game's own grass, foreshortened towards the horizon.
          float sc = 0.45f + 0.55f * s;
          const float* t = tex.at(int(x / sc + 37 * seed), int((y - horizon) / sc));
          for (int q = 0; q < 3; q++) {
            float detail = t[q] / tex.mean[q];
            p[q] *= detail;
            p[q] *= 0.92f + 0.16f * n;
          }
        }
        // distant blue hills just under the horizon
        float hill = horizon + 18 + 22 * std::sin(x * 0.03f + seed) + 14 * Fbm(x * 0.02f, 1, seed + 3);
        if (y > horizon - 30 && y < hill && y > horizon - 30 + 40 * Fbm(x * 0.015f, 2, seed)) {
          float hc[3] = {0.55f, 0.64f, 0.72f};
          Mix(p, hc, 0.7f);
        }
      } else {
        if (y < horizon) {  // night sky with a burning glow towards the horizon
          float s = float(y) / horizon;
          float top[3] = {0.02f, 0.02f, 0.03f};
          for (int q = 0; q < 3; q++) p[q] = top[q] + (th.glow[q] - top[q]) * std::pow(s, 2.2f);
          float sm = Fbm(x * 0.01f, y * 0.03f, seed + 4);
          float smoke[3] = {0.08f, 0.05f, 0.04f};
          Mix(p, smoke, std::clamp((sm - 0.45f) * 2.0f, 0.0f, 0.75f));
        } else {
          float s = (y - horizon) / (H - horizon);
          // Scorched earth: the game's grass texture as luminance, burnt red-brown.
          float sc = 0.45f + 0.55f * s;
          const float* t = tex.at(int(x / sc + 37 * seed), int((y - horizon) / sc));
          float lum = (0.3f * t[0] + 0.59f * t[1] + 0.11f * t[2]) / (0.3f * tex.mean[0] + 0.59f * tex.mean[1] + 0.11f * tex.mean[2]);
          float glow = std::pow(1 - s, 3.0f);  // the fire on the horizon lights the far ground
          for (int q = 0; q < 3; q++) p[q] = (th.ground_a[q] * glow + th.ground_b[q] * (1 - glow)) * lum * (0.85f + 0.3f * n);
        }
      }
    }

  Grade gnorm = hell ? th.dark : th.light;

  struct Item {
    const Sprite* s;
    float x, y, k;
    bool flip;
    float sil;
  };
  std::vector<Item> items;
  auto find = [&](std::vector<Sprite>& pool, const char* key) -> const Sprite* {
    std::vector<const Sprite*> m;
    for (auto& sp : pool)
      if (sp.name.find(key) != std::string::npos) m.push_back(&sp);
    return m.empty() ? nullptr : m[size_t(U(0, float(m.size()))) % m.size()];
  };
  auto any = [&](std::vector<Sprite>& pool) -> const Sprite* {
    return pool.empty() ? nullptr : &pool[size_t(U(0, float(pool.size()))) % pool.size()];
  };
  auto walker = [&]() -> const Sprite* {
    return walkers.empty() ? nullptr : &crea[walkers[size_t(U(0, float(walkers.size()))) % walkers.size()]];
  };
  // Figures shrink with distance: k at the horizon, k * 2.6 at the bottom.
  auto depthk = [&](float y, float k) {
    return k * (1.0f + 1.6f * std::clamp((y - horizon) / (H - horizon), 0.0f, 1.0f));
  };
  auto put = [&](const Sprite* sp, float x, float y, float k, float sil = 0) {
    if (sp) items.push_back({sp, x, y, k, U(0, 1) < 0.5f, sil});
  };
  // A loose crowd around (cx, cy).
  auto cluster = [&](float cx, float cy, float rx, float ry, int n, float k, const char* key = nullptr) {
    for (int i = 0; i < n; i++) {
      float a = U(0, 6.2832f), r = std::sqrt(U(0, 1));
      float x = cx + std::cos(a) * rx * r, y = cy + std::sin(a) * ry * r;
      put(key ? find(crea, key) : walker(), x, y, depthk(y, k) * U(0.85f, 1.15f));
    }
  };
  // A procession around an ellipse, every figure facing along it.
  auto ring = [&](float cx, float cy, float rx, float ry, int n, float k, const char* key) {
    for (int i = 0; i < n; i++) {
      float a = i * 6.2832f / n;
      float x = cx + std::cos(a) * rx, y = cy + std::sin(a) * ry;
      const Sprite* sp = key ? find(crea, key) : walker();
      if (sp) items.push_back({sp, x, y, depthk(y, k), std::sin(a) < 0, 0});
    }
  };
  // Scattered map objects (trees, rocks, ...) over a band of the ground.
  auto scatter = [&](float y0, float y1, int n, float k, const char* key) {
    for (int i = 0; i < n; i++) {
      float y = U(y0, y1);
      put(key ? find(obj, key) : any(obj), U(-0.05f, 1.05f) * W, y, depthk(y, k) * U(0.8f, 1.2f));
    }
  };

  if (!hell) {
    // The heavenly city on the horizon, flyers above it.
    for (int i = 0; i < 4; i++) put(any(castle), W * (0.15f + 0.23f * i), horizon + 30 + U(0, 25), 0.32f);
    scatter(horizon + 40, horizon + 300, 46, 0.22f, "trees");
    scatter(horizon + 40, H * 0.42f, 24, 0.22f, "shrubs");
    cluster(W * 0.5f, H * 0.36f, W * 0.45f, 50, 22, 0.17f);
    ring(W * 0.5f, H * 0.30f, W * 0.40f, 30, 12, 0.15f, th.ring);
    // The fountain of life: a pond in the middle with a shrine, animals around it.
    const float py = H * 0.47f;
    for (int y = int(py - 70); y < int(py + 70); y++)
      for (int x = 0; x < W; x++) {
        float dx = (x - W * 0.5f) / (W * 0.42f), dy = (y - py) / 62.0f;
        float d = dx * dx + dy * dy + 0.15f * (Fbm(x * 0.05f, y * 0.05f, seed + 2) - 0.5f);
        if (d < 1) {
          const float* wtr = th.water;
          { float rip = 0.04f * std::sin(y * 0.9f + 3 * std::sin(x * 0.07f)); float w2[3] = {wtr[0] + rip, wtr[1] + rip, wtr[2] + rip}; Mix(cv.at(x, y), w2, std::clamp((1 - d) * 30, 0.0f, 0.92f)); }
        }
      }
    put(find(obj, "shrines"), W * 0.5f, py + 8, 0.55f);
    ring(W * 0.5f, py, W * 0.47f, 78, 18, 0.20f, nullptr);
    for (const char* a : th.animals) cluster(W * U(0.2f, 0.8f), py + U(-30, 30), 40, 20, 2, 0.20f, a);
    // The grove below with monks, mages and pilgrims.
    scatter(H * 0.56f, H * 0.82f, 44, 0.24f, "trees");
    scatter(H * 0.80f, H * 0.95f, 20, 0.26f, "shrubs");
    cluster(W * 0.5f, H * 0.88f, W * 0.45f, 50, 16, 0.20f);
    scatter(H * 0.58f, H * 0.95f, 24, 0.24f, "flowers");
    cluster(W * 0.3f, H * 0.66f, 70, 60, 14, 0.18f);
    cluster(W * 0.7f, H * 0.72f, 70, 60, 14, 0.18f);
    ring(W * 0.5f, H * 0.80f, W * 0.30f, 40, 10, 0.20f, th.monks);
    // A procession of knights winding down.
    for (int i = 0; i < 10; i++) {
      float y = H * 0.55f + i * 34, x = W * (0.15f + 0.07f * i) + 18 * std::sin(i * 0.9f);
      put(find(crea, i % 2 ? th.proc_a : th.proc_b), x, y, depthk(y, 0.16f));
    }
    // The foreground: a heroine presented by an archangel, as in Eden.
    put(find(hero, th.hero), W * 0.38f, H - 70, 0.85f);
    put(find(crea, th.big), W * 0.70f, H - 40, 0.95f);
    scatter(H * 0.90f, H + 20, 10, 0.30f, "flowers");
  } else {
    // The burning city: black castles against the fire, several rows.
    for (int row = 0; row < 3; row++)
      for (int i = 0; i < 3; i++)
        put(any(castle), W * (0.1f + 0.4f * i) + U(-20, 20), horizon - 40 + row * 45, 0.30f + 0.06f * row, 0.75f);
    scatter(horizon + 60, horizon + 300, 26, 0.20f, "burned");
    scatter(horizon + 40, H * 0.36f, 26, 0.20f, "stumps");
    cluster(W * 0.5f, H * 0.33f, W * 0.45f, 45, 22, 0.16f);
    // The frozen lake with the dead skating and drowning.
    const float ly = H * 0.42f;
    for (int y = int(ly - 75); y < int(ly + 75); y++)
      for (int x = 0; x < W; x++) {
        float dx = (x - W * 0.5f) / (W * 0.46f), dy = (y - ly) / 68.0f;
        float d = dx * dx + dy * dy + 0.2f * (Fbm(x * 0.05f, y * 0.05f, seed + 2) - 0.5f);
        if (d < 1) {
          const float* ice = th.ice;
          { float cr = Fbm(x * 0.08f, y * 0.08f, seed + 21) > 0.62f ? 0.85f : 1.0f; float i2[3] = {ice[0] * cr, ice[1] * cr, ice[2] * cr}; Mix(cv.at(x, y), i2, std::clamp((1 - d) * 30, 0.0f, 0.9f)); }
        }
      }
    cluster(W * 0.5f, ly, W * 0.40f, 55, 22, 0.17f, th.lake_a);
    cluster(W * 0.5f, ly, W * 0.40f, 55, 10, 0.17f, th.lake_b);
    // The damned led in a long winding line from the lake to the giant.
    for (int i = 0; i < 16; i++) {
      float y = H * 0.47f + i * 9.5f, x = W * 0.5f + W * 0.38f * std::sin(i * 0.55f);
      put(find(crea, i % 3 ? th.line_a : th.line_b), x, y, depthk(y, 0.15f));
    }
    scatter(H * 0.46f, H * 0.56f, 14, 0.20f, "skeletons");
    cluster(W * 0.5f, H * 0.53f, W * 0.40f, 30, 10, 0.16f);
    // The giant in the middle with the crowd swarming round it.
    put(find(crea, th.giant), W * 0.5f, H * 0.62f, 0.80f);
    ring(W * 0.5f, H * 0.62f, W * 0.44f, 70, 16, 0.18f, nullptr);
    scatter(H * 0.50f, H * 0.95f, 34, 0.22f, "lava");
    scatter(H * 0.50f, H * 0.95f, 24, 0.22f, "rocks");
    scatter(H * 0.50f, H * 0.95f, 16, 0.22f, "cracks");
    cluster(W * 0.5f, H * 0.88f, W * 0.45f, 50, 18, 0.20f);
    scatter(H * 0.52f, H * 0.95f, 20, 0.22f, "skeletons");
    cluster(W * 0.25f, H * 0.74f, 70, 60, 16, 0.18f);
    cluster(W * 0.75f, H * 0.78f, 70, 60, 16, 0.18f);
    for (const char* a : th.animals) cluster(W * U(0.2f, 0.8f), H * U(0.70f, 0.86f), 50, 30, 4, 0.18f, a);
    // The prince of hell on his throne in the foreground, the damned before him.
    put(find(crea, th.big), W * 0.55f, H - 60, 1.0f);
    cluster(W * 0.5f, H - 40, W * 0.45f, 40, 10, 0.32f, th.line_a);
  }
  std::sort(items.begin(), items.end(), [](const Item& a, const Item& b) { return a.y < b.y; });
  for (const Item& it : items) {
    Grade g = gnorm;
    float depth = std::clamp((it.y - horizon) / (H - horizon), 0.0f, 1.0f);
    if (hell) {
      g.bright *= 0.7f + 0.4f * depth;
    } else {  // aerial perspective: far things pale and bluish
      g.sat *= 0.6f + 0.4f * depth;
      g.tint[2] *= 1.1f - 0.1f * depth;
    }
    Draw(cv, *it.s, it.x, it.y, it.k, it.flip, g, it.sil);
  }
  // ---- the sky's flyers, small and many, larger lower down
  for (int n = 0; n < 30 && !flyers.empty(); n++) {
    int ci = flyers[size_t(U(0, float(flyers.size()))) % flyers.size()];
    float y = U(40, horizon + 40);
    Draw(cv, crea[ci], U(0, 1) * W, y, 0.10f + 0.12f * y / horizon, U(0, 1) < 0.5f, gnorm);
  }

  // ---- finish: varnish, oil-paint grain, vignette, a thin gilt frame
  for (int y = 0; y < H; y++)
    for (int x = 0; x < W; x++) {
      float* p = cv.at(x, y);
      float grain = (Noise(x, y, seed + 99) - 0.5f) * 0.05f + (Fbm(x * 0.3f, y * 0.3f, seed + 33) - 0.5f) * 0.04f;
      float vx = (x + 0.5f) / W - 0.5f, vy = (y + 0.5f) / H - 0.5f;
      float vig = 1.0f - 0.55f * (vx * vx * 1.2f + vy * vy * 0.8f);
      float varnish[3] = {1.03f, 0.99f, 0.86f};
      for (int q = 0; q < 3; q++) p[q] = std::clamp((p[q] * varnish[q] + grain) * vig, 0.0f, 1.0f);
      int e = std::min({x, y, W - 1 - x, H - 1 - y});
      if (e < 7) {
        float gold[3] = {0.80f, 0.62f, 0.25f}, dark[3] = {0.25f, 0.16f, 0.05f};
        float t = e < 2 ? 0.0f : e < 5 ? 1.0f : 0.4f;
        float shade = 0.75f + 0.25f * std::sin((x + y) * 0.05f);
        for (int q = 0; q < 3; q++) p[q] = (dark[q] + (gold[q] - dark[q]) * t) * shade;
      }
    }

  // ---- write BMP
  FILE* f = std::fopen(argv[3], "wb");
  int row = (W * 3 + 3) & ~3;
  uint8_t hd[54] = {'B', 'M'};
  uint32_t size = 54 + row * H, off = 54, dib = 40;
  int32_t ww = W, hh = -H;
  uint16_t pl = 1, bpp = 24;
  std::memcpy(hd + 2, &size, 4);
  std::memcpy(hd + 10, &off, 4);
  std::memcpy(hd + 14, &dib, 4);
  std::memcpy(hd + 18, &ww, 4);
  std::memcpy(hd + 22, &hh, 4);
  std::memcpy(hd + 26, &pl, 2);
  std::memcpy(hd + 28, &bpp, 2);
  std::fwrite(hd, 1, 54, f);
  std::vector<uint8_t> line(row);
  for (int y = 0; y < H; y++) {
    for (int x = 0; x < W; x++) {
      float* p = cv.at(x, y);
      line[3 * x] = uint8_t(std::lround(p[2] * 255));
      line[3 * x + 1] = uint8_t(std::lround(p[1] * 255));
      line[3 * x + 2] = uint8_t(std::lround(p[0] * 255));
    }
    std::fwrite(line.data(), 1, row, f);
  }
  std::fclose(f);
  std::printf("%s: %zu creatures, %zu heroes, %zu objects, %zu castles\n", wing.c_str(), crea.size(), hero.size(), obj.size(), castle.size());
}

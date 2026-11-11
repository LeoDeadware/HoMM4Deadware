# Heroes of Might and Magic IV for Apple Silicon Macs

**Website, screenshots and install guide:** [deadware.games/heroes4](https://deadware.games/heroes4/) · [українською](https://deadware.games/uk/heroes4/)

Native macOS port of Heroes of Might and Magic IV, in English and Ukrainian. Pick your language below.<br>
Нативний порт «Героїв меча і магії IV» для macOS, англійською та українською. Оберіть мову нижче.

<details>
<summary><b>🇺🇦 Українською</b></summary>

«Герої меча і магії IV» з обома доповненнями, англійською або українською, як звичайна програма
для Мака. Без Wine, емуляторів і віртуальних машин: гра працює на Маці напряму.

- Дві мови на вибір при кожному запуску: English (оригінал) та українська (інтерфейс, кампанії,
  озвучка кампаній; доповнення The Gathering Storm лишається англійською).
- Широкий екран і чітка картинка на Retina-дисплеях.
- Плавна анімація на карті й у бою.

**Що потрібно:**

- Мак з процесором Apple (M1, M2, M3, M4 або новіший) і macOS 26 або новішою.
  Перевірити: меню  → «Про цей Mac», рядок «Чип».
- Куплена гра **Heroes of Might and Magic IV: Complete Edition** на
  [GOG](https://www.gog.com/game/heroes_of_might_and_magic_4_complete).
  Самої гри тут немає, лише те, що робить її рідною для Мака.
- Інтернет і близько 5 ГБ вільного місця.
- Приблизно 40 хвилин, з них самої роботи — хвилин 10. Решту часу Мак усе робить
  сам.

---

## Встановлення

Без Термінала й Homebrew. Гра збирається на вашому Маці з вашого інсталятора GOG,
тому в DMG немає ні коду, ні даних гри.

1. **Завантажте гру з GOG.** На [gog.com](https://www.gog.com/game/heroes_of_might_and_magic_4_complete)
   відкрийте свою бібліотеку, гру Heroes of Might and Magic IV: Complete, і завантажте
   **інсталятор для Windows** (`setup_heroes_of_might_and_magic_4_complete_….exe` і файл
   `.bin`, якщо є) у теку **«Завантаження»**.
2. Відкрийте [сторінку Releases](https://github.com/LeoDeadware/HoMM4Deadware/releases)
   і завантажте **Heroes IV.dmg**. Клацніть по ньому двічі.
3. Перетягніть **Heroes IV** у теку **Applications**.
4. **Перший запуск:** клацніть Heroes IV правою кнопкою → **«Відкрити»** →
   **«Відкрити»**. Порт не підписаний Apple, тому macOS питає один раз.
5. Мову гри (**English** або **Українська**) обираєте у вікні лаунчера при кожному запуску;
   вибір запам'ятовується.
6. Якщо на Маці немає **Command Line Tools** від Apple, відкриється системне вікно —
   натисніть **«Встановити»**. Далі Heroes IV сам знаходить інсталятор GOG у
   «Завантаженнях» (або питає, де він) і збирає гру: 15–40 хвилин, вікно з прогресом.
7. Готова гра **Heroes IV** з'являється на Робочому столі. Інсталятор GOG після
   цього можна видалити.

Ліцензії сторонніх бібліотек — у файлі «Third-party notices.txt» у DMG.

---

## Якщо щось пішло не так

**«Heroes IV не можна відкрити, бо розробника не перевірено».** Клацніть по грі правою
кнопкою → **«Відкрити»** → **«Відкрити»** (крок 4).

**Вікно пише «Гру не встановлено: …».** Найчастіше:

- **«heroes4.exe не з GOG Complete 3.0»** — у вас інша версія гри. Порт працює тільки
  з актуальною версією з GOG (інсталятор для Windows, Complete Edition).
- **«Command Line Tools не встановлено»** — у системному вікні натисніть «Встановити»,
  дочекайтеся кінця і відкрийте Heroes IV ще раз.

**Встановлення перервалося** (закрили вікно, вимкнувся Мак). Відкрийте Heroes IV ще раз:
усе, що вже зроблено, вдруге не робитиметься.

**Гра вилетіла або поводиться дивно.** Створіть
[issue](https://github.com/LeoDeadware/HoMM4Deadware/issues) і додайте до нього
два файли (у Finder: **Cmd ⌘ + Shift + G**, вставте шлях, **Enter**):

- `h4.log` з теки `~/Library/Application Support/Heroes IV/player/logs`;
- найновіший файл з теки `~/Library/Application Support/Heroes IV/player/data/h4/crashes`.

**Видалити гру:** перетягніть Heroes IV з Робочого столу й з Applications у Кошик і видаліть
теку `~/Library/Application Support/Heroes IV` (там дані гри й збереження).

## Керування

Як в оригінальній грі. Додатково: **F10** перемикає фільтр згладжування картинки.

---

## Для тих, кому цікаво, як це зроблено

Порт зроблено статичною рекомпіляцією за допомогою
[x86recomp](https://github.com/JTM-rootstorm/x86recomp): код `heroes4.exe` з
вашої копії гри заздалегідь перекладається в нативний код для Apple Silicon, а
графіка, звук і вікно працюють через SDL3 і Metal. Тому в репозиторії немає ні
коду, ні файлів гри: усе це збирається на вашому Маці з вашої копії.

| Шлях | Що |
|---|---|
| `h4/` | порт: `lifter.manifest`, замінені функції гри (`src/`) |
| `patches/` | зміни до x86recomp, що накладаються на зафіксований коміт |
| `symbols/` | адреси функцій і таблиць переходів `heroes4.exe` (з Ghidra) |
| `loc/` | український переклад (прив'язаний до хешів англійського тексту) та інструменти |
| `tools/` | DMG (`make_dmg.sh`, `dmg/`, `launcher/`), збирання з коду (`build.sh`), інструменти для арту, скрипти Ghidra |

Зібрати той самий DMG з коду (для розробників; потрібні Homebrew і ваш інсталятор GOG):
`tools/build.sh [шлях до setup_….exe]` → `.cache/dmg/Heroes IV.dmg`.

## Ліцензія

Власний код порту та інструменти — MIT (див. `LICENSE`). x86recomp — MIT від
його авторів; ffmpeg — LGPL 2.1+, решта бібліотек — див. `Third-party notices.txt` у DMG. На саму гру ліцензія не поширюється: вона ваша, з GOG.

Heroes of Might and Magic — торгова марка Ubisoft. Це фанатський проєкт, не
пов'язаний з Ubisoft чи GOG.

</details>

<details>
<summary><b>🇬🇧 English</b></summary>

Heroes of Might and Magic IV with both expansions as a regular Mac app. No Wine,
no emulators, no virtual machines: the game runs on the Mac directly.

- Two languages, chosen at every start: English (the original) and Ukrainian (interface,
  campaigns, campaign voice-over; The Gathering Storm stays in English).
- Wide screen and a sharp picture on Retina displays.
- Smooth animation on the adventure map and in combat.

**What you need:**

- A Mac with an Apple chip (M1, M2, M3, M4 or newer) running macOS 26 or later.
  To check: menu  → **About This Mac**, the **Chip** line.
- A purchased copy of **Heroes of Might and Magic IV: Complete Edition** from
  [GOG](https://www.gog.com/game/heroes_of_might_and_magic_4_complete).
  The game itself is not here, only what makes it run natively on a Mac.
- An internet connection and about 5 GB of free space.
- About 40 minutes, of which about 10 are actual work. The Mac does the rest
  on its own.

---

## Install

No Terminal, no Homebrew. The game is built on your Mac from your GOG installer,
so the DMG holds neither the game's code nor its data.

1. **Download the game from GOG.** On [gog.com](https://www.gog.com/game/heroes_of_might_and_magic_4_complete)
   open your library, Heroes of Might and Magic IV: Complete, and download the
   **Windows installer** (`setup_heroes_of_might_and_magic_4_complete_….exe`, plus the
   `.bin` file if offered) into **Downloads**.
2. Open the [Releases page](https://github.com/LeoDeadware/HoMM4Deadware/releases),
   download **Heroes IV.dmg** and double-click it.
3. Drag **Heroes IV** to **Applications**.
4. **First open:** right-click Heroes IV → **Open** → **Open**. The port is not
   signed by Apple, so macOS asks once.
5. You choose the language (**English** or **Українська**) in the launcher window at every
   start; your choice is remembered.
6. If Apple's **Command Line Tools** are missing, the system dialog opens: click
   **Install**. Heroes IV then finds the GOG installer in Downloads (or asks where
   it is) and builds the game: 15–40 minutes, with a progress window.
7. The finished **Heroes IV** appears on the Desktop. You can delete the GOG
   installer afterwards.

The licenses of the third-party libraries are in "Third-party notices.txt" in the DMG.

---

## If something goes wrong

**"Heroes IV cannot be opened because the developer cannot be verified".** Right-click
the game → **Open** → **Open** (step 4).

**The window says "Installation failed: …".** The most common ones:

- **"heroes4.exe is not from GOG Complete 3.0"**: you have a different version of the
  game. The port works only with the current GOG version (Windows installer, Complete Edition).
- **"Command Line Tools are not installed"**: click **Install** in the system dialog,
  wait until it finishes and open Heroes IV again.

**The installation was interrupted** (window closed, the Mac shut down). Open Heroes IV
again: whatever is already done is not done again.

**The game crashed or behaves oddly.** Open an
[issue](https://github.com/LeoDeadware/HoMM4Deadware/issues) and attach two files
(in Finder: **Cmd ⌘ + Shift + G**, paste the path, **Enter**):

- `h4.log` in `~/Library/Application Support/Heroes IV/player/logs`;
- the newest file in `~/Library/Application Support/Heroes IV/player/data/h4/crashes`.

**To remove the game:** drag Heroes IV from the Desktop and from Applications to the Trash
and delete the folder `~/Library/Application Support/Heroes IV` (game data and saves).

## Controls

As in the original game. In addition, **F10** switches the picture smoothing filter.

---

## How it is made

The port is made by static recompilation with
[x86recomp](https://github.com/JTM-rootstorm/x86recomp): the code of `heroes4.exe`
from your copy of the game is translated ahead of time into native Apple
Silicon code, while graphics, sound and the window run on SDL3 and Metal. That
is why the repository holds no game code or files: all of it is built on your
Mac from your copy.

| Path | What |
|---|---|
| `h4/` | the port: `lifter.manifest`, replaced game functions (`src/`) |
| `patches/` | changes to x86recomp, applied on a pinned commit |
| `symbols/` | function and jump-table addresses of `heroes4.exe` (from Ghidra) |
| `loc/` | the Ukrainian translation (keyed by hashes of the English text) and its tools |
| `tools/` | the DMG (`make_dmg.sh`, `dmg/`, `launcher/`), the source build (`build.sh`), art tools, Ghidra scripts |

To build the same DMG from source (for developers; needs Homebrew and your GOG installer):
`tools/build.sh [path to setup_….exe]` → `.cache/dmg/Heroes IV.dmg`.

## License

The port's own code and tools: MIT (see `LICENSE`). x86recomp: MIT, by its
authors; ffmpeg: LGPL 2.1+; the other libraries: see `Third-party notices.txt` in the DMG. The license does not cover the game itself: it stays yours, from GOG.

Heroes of Might and Magic is a trademark of Ubisoft. This is a fan project,
unaffiliated with Ubisoft or GOG.

</details>

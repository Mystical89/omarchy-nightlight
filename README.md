**English** | [Русский](#русский)

# Sunset Night Light for Omarchy

An [Omarchy](https://omarchy.org) shell plugin that warms your screen at your
local sunset instead of at fixed times. It also adds a bar icon that shows what
the night light is doing and lets you override it.

![The night light popup](preview.png)

- **Follows the sun.** Every day it works out sunset for your location and
  schedules [hyprsunset](https://github.com/hyprwm/hyprsunset):
  - 3400K at sunset
  - 2700K three hours later
  - off at 07:00

  All of these are configurable.
- **Bar icon.** A moon appears in the evening, or while an override is on, and
  is hidden during the day. It is highlighted while an override is on and
  shows a warning if hyprsunset stops responding.
- **Popup.** Shows today's schedule, preset buttons (Off, the scheduled
  temperatures), a temperature slider, and how long to hold an override: until
  the next scheduled change, for an hour, or until morning. *Resume schedule*
  ends an override.
- **Overrides persist.** hyprsunset normally drops a manual temperature at its
  next scheduled switch. The plugin re-applies an override until it expires,
  even across hyprsunset restarts.

## Install

```bash
omarchy plugin add https://github.com/Mystical89/omarchy-nightlight.git --enable
```

This is a fork of
[agkrishnendu/omarchy-nightlight](https://github.com/agkrishnendu/omarchy-nightlight)
— see [This fork](#this-fork) for what it changes. It keeps the upstream
plugin id `io.github.agkrishnendu.nightlight`, so installing it replaces an
upstream copy and the bar entry keeps working.

Then click the moon in the bar and choose **Enable sunset schedule**.

**The plugin changes nothing until you enable it.** Enabling does two things:

1. It moves your `~/.config/hypr/hyprsunset.conf` to
   `~/.config/hypr/hyprsunset.conf.pre-nightlight`.
2. It replaces that file with a generated schedule, which it rewrites daily as
   sunset shifts.

Until you enable it, the moon stays in the bar with a setup prompt, and the
plugin doesn't touch your files or hyprsunset.

To update, run `omarchy plugin update io.github.agkrishnendu.nightlight`, then
`omarchy restart shell`. Without the restart, the shell's hot reload can leave
the old copy of the widget running alongside the new one.

### The built-in night light toggle is removed for you

Omarchy's indicators widget has its own night light toggle, which switches
between 4000K and 6500K and ignores the schedule. One click on it silently
overrides the schedule until the next profile switch.

This fork removes it from the bar when you enable the plugin: every indicators
widget in `~/.config/omarchy/shell.json` loses `NightLight` from its `items`
list (the file is backed up once as `shell.json.pre-nightlight`, and only that
key is touched). `nightlight-schedule disable` puts the list back exactly as it
was.

The `SUPER+CTRL+N` binding still runs the old toggle, because the plugin can't
own a keybinding without rewriting `~/.config/hypr/bindings.lua`. `enable` prints
the two lines to paste there:

```lua
hl.unbind("SUPER + CTRL + N")
o.bind("SUPER + CTRL + N", "Night light", "omarchy-shell io.github.agkrishnendu.nightlight toggle")
```

then `hyprctl reload`. `status --json` reports the state as
`bar.nightLightToggleHidden`.

## Dependencies

| Dependency | Needed for | Notes |
|------------|------------|-------|
| [hyprsunset](https://github.com/hyprwm/hyprsunset) | Changing the screen temperature | Ships with Omarchy. The plugin starts it if it isn't running. |
| `python3` | The schedule script | Ships with Omarchy. Uses the standard library only. |
| `hyprctl`, `pgrep`, `pkill` | Talking to and restarting hyprsunset | Ship with Hyprland and Arch. |
| `uwsm-app` | Starting hyprsunset in its own systemd scope | Ships with Omarchy. Falls back to a detached process without it. |
| Network access to [wttr.in](https://wttr.in) | Finding your location from your IP address | Only used when the weather widget has no location set. The result is cached. |

## Using it

| On the bar icon | Does |
|-----------------|------|
| Left click      | Open the popup |
| Right click     | Turn off until the next scheduled change, or resume the schedule if an override is on |
| Middle click    | Refresh |

The icon is hidden during the day once the plugin is enabled. To open the
popup anyway, for example from a keybinding, run:

```bash
omarchy-shell io.github.agkrishnendu.nightlight open    # also: close, toggle, refresh, resume
```

## Settings

Edit these in the Omarchy settings panel, or on the plugin's entry in
`shell.json`:

| Key | Default | Meaning |
|-----|---------|---------|
| `eveningTemperature` | `3400` | Kelvin applied at sunset |
| `lateTemperature` | `2700` | Kelvin applied later in the evening |
| `lateAfterMinutes` | `180` | Minutes after sunset to switch to the late temperature; `0` disables it |
| `offTime` | `"07:00"` | When the filter turns off in the morning |

Changes apply at the widget's next check, within 30 seconds.

### Location

The plugin uses the location set in Omarchy's weather widget (click the place
name in the weather popup). Without one, it detects your location from your IP
address through wttr.in and caches the result.

## Command line

The widget is a thin front end to the bundled `src/nightlight-schedule.py`,
which you can also run yourself:

```bash
S=~/.config/omarchy/plugins/io.github.agkrishnendu.nightlight/src/nightlight-schedule.py
$S enable                         # back up hyprsunset.conf and start the schedule
$S status                         # now 3400K, 2700K at 21:18
$S set 2700 --until morning       # --until next | morning | 1h | 30m | HH:MM
$S set off                        # off until the next scheduled change
$S resume                         # back to the schedule
$S restart                        # if hyprsunset stops answering
$S disable                        # restore your hyprsunset.conf
$S status --json                  # what the widget reads
```

To make it a command, symlink it onto your `PATH`:

```bash
ln -s ~/.config/omarchy/plugins/io.github.agkrishnendu.nightlight/src/nightlight-schedule.py ~/.local/bin/nightlight-schedule
```

## How it works

- Once enabled, it writes `~/.config/hypr/hyprsunset.conf` with the day's
  profiles. It rewrites the file only when the date, your settings or the
  weather location has changed, and restarts hyprsunset only if the file
  actually changed.
- The first line of the generated file marks it as the plugin's. The plugin
  never rewrites a `hyprsunset.conf` without that line, so if something else
  replaces the file (for example `omarchy refresh`), the plugin stops and asks
  to be enabled again.
- The widget runs `nightlight-schedule sync` every 30 seconds and again right
  after each scheduled change. When enabled, `sync` does three things:
  1. starts hyprsunset if it isn't running
  2. refreshes the profiles when needed
  3. re-applies an active override, or retries a restore that didn't land
- Its state is kept in `~/.local/state/nightlight-schedule/`: the override,
  the last settings used, and the cached coordinates. State files are replaced
  atomically and checked when read; one that doesn't hold what the plugin
  writes is moved aside as `<name>.bad` and rebuilt.
- Ending an override (by `resume` or by expiry) owes the screen its scheduled
  temperature. If hyprsunset doesn't take it, the debt is kept and the next
  `sync` tries again, rather than leaving the override on screen until the next
  scheduled change.
- Your morning off time bounds the night: an evening or late profile that would
  land on or after it is dropped. If sunset itself falls on your off time, that
  day has no night window.

## Uninstall

First give your `hyprsunset.conf` back. Either open the popup and click
**Disable and restore hyprsunset.conf** (it asks you to click twice), or run:

```bash
~/.config/omarchy/plugins/io.github.agkrishnendu.nightlight/src/nightlight-schedule.py disable
```

This moves `hyprsunset.conf.pre-nightlight` back into place, restarts
hyprsunset with it, deletes the plugin's state and, in this fork, puts
`NightLight` back into the bar's indicators list. If you had no
`hyprsunset.conf` before, it removes the generated file and stops hyprsunset
instead. Then remove the plugin:

```bash
omarchy plugin remove io.github.agkrishnendu.nightlight
rm -rf ~/.local/state/nightlight-schedule   # optional: the cached location
```

`omarchy plugin remove` only unloads the widget and deletes the folder; the bar
entry stays in `shell.json`, so a later install brings it back.

## This fork

Fork of [agkrishnendu/omarchy-nightlight](https://github.com/agkrishnendu/omarchy-nightlight)
that deals with Omarchy's own night light toggle for you:

- `enable` removes `NightLight` from the `items` list of every indicators
  widget in `~/.config/omarchy/shell.json` (the file is backed up once as
  `shell.json.pre-nightlight`, and the previous lists are remembered in
  `~/.local/state/nightlight-schedule/indicators.json`);
- `disable` puts those lists back exactly as they were;
- `enable` prints the two `bindings.lua` lines that point `SUPER+CTRL+N` at the
  plugin popup — the plugin doesn't rewrite your keybindings on its own;
- `status --json` reports the state as `bar.nightLightToggleHidden`.

Everything else is upstream's. The new logic lives in
`src/nightlight/indicators.py` and is covered by `tests/test_indicators.py`.

## Development

```
manifest.json               plugin manifest and settings schema
Panel.qml                   bar icon and popup; renders `status --json`
preview.png                 marketplace preview
src/nightlight-schedule.py  command entry point
src/nightlight/
  config.py                 paths, defaults, state files
  sun.py                    location lookup and sunset calculation
  hyprsunset.py             hyprctl IPC, starting and stopping hyprsunset
  lifecycle.py              enable (with consent) and disable (restore)
  indicators.py             hiding Omarchy's own night light toggle in shell.json
  profiles.py               generating and reading hyprsunset.conf
  schedule.py               time logic over the daily profiles (no I/O)
  override.py               overrides and keeping them applied
  status.py                 the status report
  cli.py                    argument parsing and `sync`
tests/                      unit tests (standard library only)
```

Run the tests and check the plugin before you push:

```bash
python3 -B -m unittest discover -s tests
omarchy plugin validate .
```

`.github/workflows/ci.yml` runs the tests on pushes and pull requests
(`omarchy plugin validate` needs Omarchy, so it stays a local check).

The tests point every path at a temporary directory and replace hyprsunset
with a stub, so they never touch your screen or config.

## License

[MIT](LICENSE)

---

## Русский

[↑ English](#sunset-night-light-for-omarchy)

Плагин shell для [Omarchy](https://omarchy.org): делает экран тёплым по
местному закату, а не по фиксированному времени. Добавляет иконку в бар,
которая показывает, что происходит с ночным режимом, и позволяет его
переопределить.

![Попап ночного режима](preview.png)

- **Следует за солнцем.** Каждый день вычисляет закат для вашей локации и
  планирует [hyprsunset](https://github.com/hyprwm/hyprsunset):
  - 3400K на закате;
  - 2700K через три часа;
  - выключение в 07:00.

  Всё это настраивается.
- **Иконка в баре.** Луна появляется вечером или пока действует
  переопределение; днём скрыта. Подсвечивается при активном переопределении и
  показывает предупреждение, если hyprsunset перестал отвечать.
- **Попап.** Расписание на сегодня, кнопки-пресеты (Выкл, запланированные
  температуры), слайдер температуры и длительность переопределения: до
  следующего изменения по расписанию, на час или до утра. *Resume schedule*
  завершает переопределение.
- **Переопределения живут до срока.** hyprsunset обычно сбрасывает ручную
  температуру на следующем переключении; плагин переприменяет её, пока не
  истечёт срок, в том числе после перезапуска hyprsunset.

### Установка

```bash
omarchy plugin add https://github.com/Mystical89/omarchy-nightlight.git --enable
```

Это форк
[agkrishnendu/omarchy-nightlight](https://github.com/agkrishnendu/omarchy-nightlight)
(отличия — в разделе «Этот форк» ниже). ID плагина оставлен апстримным
(`io.github.agkrishnendu.nightlight`), поэтому установка заменяет апстримную
копию, а запись в баре продолжает работать.

Затем нажмите на луну в баре и выберите **Enable sunset schedule**.

**До включения плагин ничего не меняет.** Включение делает две вещи:

1. Переносит `~/.config/hypr/hyprsunset.conf` в
   `~/.config/hypr/hyprsunset.conf.pre-nightlight`.
2. Заменяет этот файл сгенерированным расписанием, которое перезаписывается
   каждый день по мере сдвига заката.

Пока плагин не включён, луна висит в баре с приглашением к настройке, и плагин
не трогает ни ваши файлы, ни hyprsunset.

Обновление: `omarchy plugin update io.github.agkrishnendu.nightlight`, затем
`omarchy restart shell` — без перезапуска hot reload может оставить старую
копию виджета работать рядом с новой.

#### Встроенный тумблер ночного режима убирается автоматически

У виджета индикаторов Omarchy есть собственный тумблер ночного режима: он
переключает 4000K и 6500K и ничего не знает о расписании. Один клик по нему
молча переопределяет расписание до следующего переключения профиля.

Этот форк убирает тумблер при включении плагина: у каждого виджета индикаторов
в `~/.config/omarchy/shell.json` из списка `items` пропадает `NightLight`
(файл однократно бэкапится как `shell.json.pre-nightlight`, трогается только
этот ключ). `nightlight-schedule disable` возвращает список ровно как было.

Биндинг `SUPER+CTRL+N` по-прежнему запускает старый тумблер: плагин не
переписывает `~/.config/hypr/bindings.lua` сам. `enable` печатает две строки,
которые нужно вставить туда:

```lua
hl.unbind("SUPER + CTRL + N")
o.bind("SUPER + CTRL + N", "Night light", "omarchy-shell io.github.agkrishnendu.nightlight toggle")
```

затем `hyprctl reload`. Состояние видно в `status --json` как
`bar.nightLightToggleHidden`.

### Зависимости

| Зависимость | Для чего | Заметки |
|---|---|---|
| [hyprsunset](https://github.com/hyprwm/hyprsunset) | Меняет температуру экрана | Идёт с Omarchy. Плагин запускает его, если тот не работает. |
| `python3` | Скрипт расписания | Идёт с Omarchy. Только стандартная библиотека. |
| `hyprctl`, `pgrep`, `pkill` | Общение с hyprsunset и его перезапуск | Идут с Hyprland и Arch. |
| `uwsm-app` | Запуск hyprsunset в отдельном systemd-скоупе | Идёт с Omarchy. Без него — отсоединённый процесс. |
| Сеть до [wttr.in](https://wttr.in) | Определение локации по IP | Только если в виджете погоды не задана локация. Результат кешируется. |

### Использование

| На иконке в баре | Что делает |
|---|---|
| Левый клик | Открыть попап |
| Правый клик | Выключить до следующего изменения по расписанию или вернуть расписание, если действует переопределение |
| Средний клик | Обновить |

После включения иконка днём скрыта. Чтобы открыть попап всё равно, например с
биндинга:

```bash
omarchy-shell io.github.agkrishnendu.nightlight open    # также: close, toggle, refresh, resume
```

### Настройки

Правятся в панели настроек Omarchy или в записи плагина в `shell.json`:

| Ключ | По умолчанию | Смысл |
|---|---|---|
| `eveningTemperature` | `3400` | Кельвины на закате |
| `lateTemperature` | `2700` | Кельвины позже вечером |
| `lateAfterMinutes` | `180` | Через сколько минут после заката переключаться на позднюю температуру; `0` отключает |
| `offTime` | `"07:00"` | Когда фильтр выключается утром |

Изменения применяются на следующей проверке виджета, в течение 30 секунд.

#### Локация

Плагин берёт локацию из виджета погоды Omarchy (клик по названию места в
попапе погоды). Если её нет — определяет по IP через wttr.in и кеширует
результат.

### Командная строка

Виджет — тонкая обёртка над `src/nightlight-schedule.py`, который можно
запускать и самому:

```bash
S=~/.config/omarchy/plugins/io.github.agkrishnendu.nightlight/src/nightlight-schedule.py
$S enable                         # бэкап hyprsunset.conf и запуск расписания
$S status                         # сейчас 3400K, 2700K в 21:18
$S set 2700 --until morning       # --until next | morning | 1h | 30m | HH:MM
$S set off                        # выключить до следующего изменения
$S resume                         # вернуться к расписанию
$S restart                        # если hyprsunset перестал отвечать
$S disable                        # вернуть ваш hyprsunset.conf
$S status --json                  # то, что читает виджет
```

Чтобы сделать из него команду, поставьте симлинк в `PATH`:

```bash
ln -s ~/.config/omarchy/plugins/io.github.agkrishnendu.nightlight/src/nightlight-schedule.py ~/.local/bin/nightlight-schedule
```

### Как это работает

- После включения плагин пишет `~/.config/hypr/hyprsunset.conf` с профилями на
  день. Файл перезаписывается только при смене даты, настроек или локации, а
  hyprsunset перезапускается только если файл действительно изменился.
- Первая строка сгенерированного файла помечает его как файл плагина. Плагин
  никогда не перезаписывает `hyprsunset.conf` без этой строки: если файл
  заменило что-то другое (например `omarchy refresh`), плагин останавливается
  и просит включить его заново.
- Виджет запускает `nightlight-schedule sync` каждые 30 секунд и сразу после
  каждого запланированного изменения. Когда плагин включён, `sync` делает три
  вещи: запускает hyprsunset, если тот не работает; обновляет профили при
  необходимости; переприменяет активное переопределение или повторяет
  восстановление, которое не удалось.
- Состояние лежит в `~/.local/state/nightlight-schedule/`: переопределение,
  последние настройки и кешированные координаты. Файлы заменяются атомарно и
  проверяются при чтении; файл, не соответствующий ожиданиям, откладывается
  как `<имя>.bad` и пересобирается.
- Завершение переопределения (`resume` или истечение срока) оставляет за
  экраном запланированную температуру. Если hyprsunset её не принял, долг
  сохраняется, и следующий `sync` пробует снова, а не оставляет
  переопределение на экране до следующего изменения.
- Утреннее время выключения ограничивает ночь: вечерний или поздний профиль,
  попадающий на него или позже, отбрасывается. Если сам закат попадает на время
  выключения, ночного окна в этот день нет.

### Удаление

Сначала верните свой `hyprsunset.conf`. Либо откройте попап и нажмите
**Disable and restore hyprsunset.conf** (он попросит нажать дважды), либо
запустите:

```bash
~/.config/omarchy/plugins/io.github.agkrishnendu.nightlight/src/nightlight-schedule.py disable
```

Это вернёт `hyprsunset.conf.pre-nightlight` на место, перезапустит hyprsunset с
ним, удалит состояние плагина и — в этом форке — вернёт `NightLight` в список
индикаторов бара. Если до плагина файла `hyprsunset.conf` не было, команда
удаляет сгенерированный файл и останавливает hyprsunset. Затем удалите плагин:

```bash
omarchy plugin remove io.github.agkrishnendu.nightlight
rm -rf ~/.local/state/nightlight-schedule   # опционально: кеш локации
```

`omarchy plugin remove` только выгружает виджет и удаляет каталог; запись в
`shell.json` остаётся, поэтому повторная установка её вернёт.

### Этот форк

Форк [agkrishnendu/omarchy-nightlight](https://github.com/agkrishnendu/omarchy-nightlight),
который сам разбирается со встроенным тумблером ночного режима Omarchy:

- `enable` убирает `NightLight` из `items` каждого виджета индикаторов в
  `~/.config/omarchy/shell.json` (файл однократно бэкапится как
  `shell.json.pre-nightlight`, прежние списки запоминаются в
  `~/.local/state/nightlight-schedule/indicators.json`);
- `disable` возвращает эти списки ровно как было;
- `enable` печатает две строки для `bindings.lua`, перенаправляющие
  `SUPER+CTRL+N` на попап плагина — сам плагин биндинги не переписывает;
- `status --json` сообщает состояние как `bar.nightLightToggleHidden`.

Всё остальное — апстримное. Новая логика в `src/nightlight/indicators.py`,
тесты — `tests/test_indicators.py`.

### Лицензия

[MIT](LICENSE)

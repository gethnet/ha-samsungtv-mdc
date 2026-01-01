# Samsung MDC Home Assistant Integration

Custom Home Assistant integration for Samsung commercial displays that support the MDC (Multiple Display Control) protocol. It uses the [`python-samsung-mdc`](https://pypi.org/project/python-samsung-mdc/) library to power on/off, change inputs, adjust volume, and send virtual remote key presses over Ethernet.

## Features
- Media Player entity (power, mute, volume set, input/source selection)
- Backlight (manual lamp) and color temperature controls
- Remote entity that forwards Home Assistant `remote.send_command` calls as MDC virtual remote keys
- Config Flow UI (no YAML) with optional TLS PIN for secured MDC
- Periodic polling with configurable interval and timeout
- Ticker overlay helper (scrolling message on the display)

## Installation
1. Copy the `samsungtv_mdc` folder into your Home Assistant `custom_components` directory.
2. Restart Home Assistant.
3. In **Settings → Devices & Services**, click **Add Integration**, search for **SamsungTV MDC**, and follow the prompts.

## Configuration
| Field | Description |
| --- | --- |
| Host | IP or hostname of the display (TCP MDC port 1515 by default) |
| Port | MDC port, defaults to 1515 |
| Display ID | MDC display ID (commonly 0 or 1) |
| TLS PIN | Optional 4‑digit PIN when Secure MDC is enabled |
| Name | Friendly name used for the entities |

### Options
- **Update interval**: how often to poll status (seconds)
- **Command timeout**: per-command timeout (seconds)

## Usage
- Control power/volume/source via the created media player entity.
- Send remote key codes with `remote.send_command`. Commands accept either `KEY_POWER` style strings or friendly names like `power`, `volume_up`, etc.
- Example service call:
  ```yaml
  service: remote.send_command
  target:
    entity_id: remote.lobby_display_remote
  data:
    command:
      - power
      - volume_up
  ```

### Backlight / Color Temperature
```yaml
service: media_player.set_backlight
target:
  entity_id: media_player.lobby_display
data:
  brightness: 75
```

```yaml
service: media_player.set_color_temperature
target:
  entity_id: media_player.lobby_display
data:
  color_temperature: 50  # hectoKelvin, e.g. 50 -> 5000K
```

### Ticker Overlay
```yaml
service: media_player.send_ticker
target:
  entity_id: media_player.lobby_display
data:
  message: "Meeting starts in 5 minutes"
  position_horizontal: left
  motion_on: true
  motion_direction: right
  motion_speed: slow
```

## Testing
Install test dependencies with `pip install -r requirements_test.txt` and run:
```bash
pytest
```

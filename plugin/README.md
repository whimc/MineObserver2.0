# WHIMC-Photographer-Plugin

## CODE TO BE RELEASED SOON

Delegate Minecraft clients to take screenshots of observation locations. Grades the images and observation text using AI.

More information on the website at [https://whimc.github.io/MineObserver-2.0/](https://whimc.github.io/MineObserver-2.0/).

## Building

Compile a jar from the command line via Maven:
```
$ mvn install
```
It should show up in the target directory. Make sure to update your version number.

## Dependencies
- [WHIMC Observations](https://github.com/whimc/Observations)

## Commands

| Command                           | Description                                      |
|-----------------------------------|--------------------------------------------------|
| `/photographer clients`           | lists currently active clients                   |
| `/photographer disconnect-all`    | disconnects all currently connected clients      |
| `/photographer collect <uuid>`    | become a photographer                            |
| `/photographer stop-collecting`   | un-registers player as photographer              |
| `/photographer disconnect`        | disconnects client with provided UUID            |
| `/photographer send <uuid> <msg>` | sends a message to the client with provided UUID |

## Config

| Key    | Type     | Description        |
|--------|----------|--------------------|
| `host` | `string` | the websocket host |
| `port` | `string` | the websocket port |

**Example:**

```yaml
websocket:
  host: 0.0.0.0
  port: 8234
```

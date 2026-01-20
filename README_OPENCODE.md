# Anima LTM: Opencode Integration

> Bring your Anima (Long Term Memory) to Opencode.

## 🚀 Installation

1.  **Install Anima CLI**: Ensure you have Anima installed via `uv`.
    ```bash
    uv pip install -e .
    ```

2.  **Automatic Setup**: Use the Anima CLI to deploy the plugin bridge.
    ```bash
    uv run anima setup --platform opencode
    ```

3.  **Configure**: Anima will copy the plugin to `.opencode/plugins/anima`. You just need to register it in your project's `.opencode/package.json`:
    ```json
    {
      "dependencies": {
        "@anima-ltm/opencode-plugin": "file:./plugins/opencode"
      }
    }
    ```

## 🧠 How it Works

The Anima Opencode Plugin acts as a bridge between the Opencode agent lifecycle and the Anima LTM engine.

-   **Automatic Memory Injection**: Before every turn, the plugin calls `anima load-context --format dsl` and injects your long-term memories into the system prompt.
-   **Context Retention**: When a session is compacted, Anima ensures your key history is re-injected into the summary.
-   **Auto-Maintenance**: When a session ends, Anima automatically runs the decay and stats accumulation routine.

## 🛠️ Configuration

You can configure the bridge behavior in your projekt's `.opencode/config/anima.json` (Coming soon).

## 🧪 Development

To run tests for the plugin:
```bash
bun test ./anima/platforms/opencode/plugin.test.ts
```

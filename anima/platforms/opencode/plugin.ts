import type { Plugin } from "@opencode-ai/plugin"
import { homedir } from "os"
import { join } from "path"

/**
 * Anima LTM Plugin for Opencode
 * 
 * Bridges Opencode sessions to the Anima Long Term Memory layer.
 */
export const AnimaPlugin: Plugin = async ({ client, $, directory }) => {
    const CACHE_TTL = 300000 // 5 minutes
    let memoryCache = {
        dsl: "",
        timestamp: 0
    }

    const logEvent = (event: string, details: any = {}, level: "info" | "error" | "warn" = "info") => {
        client.app.log({
            service: "anima-ltm",
            level,
            message: event,
            extra: details
        })
    }

    const loadAnimaContext = async (force: boolean = false): Promise<string> => {
        const now = Date.now()
        if (!force && memoryCache.dsl && (now - memoryCache.timestamp) < CACHE_TTL) {
            return memoryCache.dsl
        }

        try {
            // Direct call to anima CLI with dsl format
            const result = await $`uv run anima load-context --format dsl`
            const dsl = String(result.stdout || "").trim()

            if (dsl) {
                memoryCache = { dsl, timestamp: now }
                logEvent("context_loaded", { tokens: dsl.length })
            }
            return dsl
        } catch (error: any) {
            logEvent("load_failed", { error: error.message }, "error")
            return ""
        }
    }

    // Initial load
    await loadAnimaContext(true)

    return {
        /**
         * Inject memories into the system prompt for every turn.
         */
        "experimental.chat.system.transform": async (input, output) => {
            try {
                const dsl = await loadAnimaContext()
                if (dsl) {
                    output.system.push(`\n${dsl}\n\n# These are your long-term memories. Use them to maintain continuity.`)
                }
            } catch (error: any) {
                logEvent("transform_failed", { error: error.message }, "error")
            }
        },

        /**
         * Ensure memories survive session compaction.
         */
        "experimental.session.compacting": async (input, output) => {
            try {
                const dsl = await loadAnimaContext()
                if (dsl) {
                    // Inject into compaction context to guide the summary
                    output.context.push(dsl)
                    logEvent("compaction_injection_success")
                }
            } catch (error: any) {
                logEvent("compaction_injection_failed", { error: error.message }, "error")
            }
        },

        /**
         * Run maintenance at the end of the session.
         */
        "session.end": async (input, output) => {
            try {
                await $`uv run anima end-session`
                logEvent("session_end_maintenance_complete")
            } catch (error: any) {
                logEvent("maintenance_failed", { error: error.message }, "error")
            }
        }
    }
}

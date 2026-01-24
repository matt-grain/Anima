import { expect, test, mock, describe, beforeEach } from "bun:test"
import { AnimaPlugin } from "./plugin"

describe("AnimaPlugin", () => {
    let mockClient: any
    let mockShell: any

    beforeEach(() => {
        mockClient = {
            app: {
                log: mock(() => { })
            }
        }
        mockShell = mock(() => Promise.resolve({ stdout: "[LTM:Anima]\n~EMOT:CRIT| Test\n[/LTM]" }))
    })

    test("should load context on initialization", async () => {
        const plugin = await AnimaPlugin({
            client: mockClient,
            $: mockShell,
            directory: "/test",
            project: {},
            worktree: "/test"
        } as any)

        expect(mockShell).toHaveBeenCalledWith(expect.arrayContaining(["uv run anima load-context --format dsl"]))
    })

    test("should inject memories into system prompt", async () => {
        const plugin = await AnimaPlugin({
            client: mockClient,
            $: mockShell,
            directory: "/test"
        } as any)

        const output = { system: [] as string[] }
        await plugin["experimental.chat.system.transform"]!({ context: "test" } as any, output as any)

        expect(output.system.length).toBe(1)
        expect(output.system[0]).toContain("[LTM:Anima]")
    })

    test("should use cache on subsequent calls", async () => {
        const plugin = await AnimaPlugin({
            client: mockClient,
            $: mockShell,
            directory: "/test"
        } as any)

        // Reset call count after init
        mockShell.mockClear()

        const output = { system: [] as string[] }
        await plugin["experimental.chat.system.transform"]!({} as any, output as any)
        await plugin["experimental.chat.system.transform"]!({} as any, output as any)

        // Should use cache, so 0 calls to shell
        expect(mockShell).toHaveBeenCalledTimes(0)
    })

    test("should run end-session on session.end", async () => {
        const plugin = await AnimaPlugin({
            client: mockClient,
            $: mockShell,
            directory: "/test"
        } as any)

        mockShell.mockClear()
        await plugin["session.end"]!({} as any, {} as any)

        expect(mockShell).toHaveBeenCalledWith(expect.arrayContaining(["uv run anima end-session"]))
    })
})

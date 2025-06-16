from pydantic_ai.mcp import MCPServerStdio

filesystem_mcp = MCPServerStdio(
    command="npx",
    args=[
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "."
    ],
)
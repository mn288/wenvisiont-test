from fastapi import FastAPI
from mcp.server.fastmcp import FastMCP
import math

# import sympy as sp
# Initialize FastMCP with SSE enabled
mcp = FastMCP("Math Server", host="0.0.0.0")


@mcp.tool()
def add(a: float, b: float) -> float:
    """Add two numbers"""
    return a + b


@mcp.tool()
def subtract(a: float, b: float) -> float:
    """Subtract b from a"""
    return a - b


@mcp.tool()
def multiply(a: float, b: float) -> float:
    """Multiply two numbers"""
    return a * b


@mcp.tool()
def divide(a: float, b: float) -> float:
    """Divide a by b"""
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b


@mcp.tool()
def sqrt(x: float) -> float:
    """Calculate the square root of x"""
    return math.sqrt(x)


@mcp.tool()
def power(x: float, y: float) -> float:
    """Calculate x raised to the power of y"""
    return x**y


# Expose the ASGI app for uvicorn


mcp_app = mcp.sse_app()
app = FastAPI()


@app.get("/health")
async def health():
    return {"status": "ok"}


app.mount("/", mcp_app)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

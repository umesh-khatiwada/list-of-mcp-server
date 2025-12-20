# A comprehensive MCP server exposing mathematical functions
import math

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("math-mcp")


# Basic Arithmetic Operations
@mcp.tool(name="add", description="Add two numbers")
def add(a: float, b: float) -> float:
    """Add two numbers."""
    try:
        result = a + b
        return result
    except Exception as e:
        return f"Error in addition: {e}"


@mcp.tool(name="subtract", description="Subtract second number from first number")
def subtract(a: float, b: float) -> float:
    """Subtract b from a."""
    try:
        result = a - b
        return result
    except Exception as e:
        return f"Error in subtraction: {e}"


@mcp.tool(name="multiply", description="Multiply two numbers")
def multiply(a: float, b: float) -> float:
    """Multiply two numbers."""
    try:
        result = a * b
        return result
    except Exception as e:
        return f"Error in multiplication: {e}"


@mcp.tool(name="divide", description="Divide first number by second number")
def divide(a: float, b: float) -> float:
    """Divide a by b."""
    try:
        if b == 0:
            return "Error: Division by zero is not allowed"
        result = a / b
        return result
    except Exception as e:
        return f"Error in division: {e}"


@mcp.tool(
    name="modulo",
    description="Calculate remainder when first number is divided by second number",
)
def modulo(a: float, b: float) -> float:
    """Calculate a modulo b."""
    try:
        if b == 0:
            return "Error: Modulo by zero is not allowed"
        result = a % b
        return result
    except Exception as e:
        return f"Error in modulo: {e}"


# Power and Root Operations
@mcp.tool(name="power", description="Raise first number to the power of second number")
def power(base: float, exponent: float) -> float:
    """Calculate base raised to the power of exponent."""
    try:
        result = base**exponent
        return result
    except Exception as e:
        return f"Error in power calculation: {e}"


@mcp.tool(name="square_root", description="Calculate square root of a number")
def square_root(x: float) -> float:
    """Calculate square root of x."""
    try:
        if x < 0:
            return "Error: Cannot calculate square root of negative number"
        result = math.sqrt(x)
        return result
    except Exception as e:
        return f"Error in square root: {e}"


@mcp.tool(name="cube_root", description="Calculate cube root of a number")
def cube_root(x: float) -> float:
    """Calculate cube root of x."""
    try:
        result = x ** (1 / 3) if x >= 0 else -((-x) ** (1 / 3))
        return result
    except Exception as e:
        return f"Error in cube root: {e}"


# Trigonometric Functions
@mcp.tool(name="sin", description="Calculate sine of angle in radians")
def sin(x: float) -> float:
    """Calculate sine of x (in radians)."""
    try:
        result = math.sin(x)
        return result
    except Exception as e:
        return f"Error in sine: {e}"


@mcp.tool(name="cos", description="Calculate cosine of angle in radians")
def cos(x: float) -> float:
    """Calculate cosine of x (in radians)."""
    try:
        result = math.cos(x)
        return result
    except Exception as e:
        return f"Error in cosine: {e}"


@mcp.tool(name="tan", description="Calculate tangent of angle in radians")
def tan(x: float) -> float:
    """Calculate tangent of x (in radians)."""
    try:
        result = math.tan(x)
        return result
    except Exception as e:
        return f"Error in tangent: {e}"


# Logarithmic Functions
@mcp.tool(name="log", description="Calculate natural logarithm of a number")
def log(x: float) -> float:
    """Calculate natural logarithm of x."""
    try:
        if x <= 0:
            return "Error: Logarithm of non-positive number is undefined"
        result = math.log(x)
        return result
    except Exception as e:
        return f"Error in logarithm: {e}"


@mcp.tool(name="log10", description="Calculate base-10 logarithm of a number")
def log10(x: float) -> float:
    """Calculate base-10 logarithm of x."""
    try:
        if x <= 0:
            return "Error: Logarithm of non-positive number is undefined"
        result = math.log10(x)
        return result
    except Exception as e:
        return f"Error in log10: {e}"


@mcp.tool(name="exp", description="Calculate e raised to the power of x")
def exp(x: float) -> float:
    """Calculate e^x."""
    try:
        result = math.exp(x)
        return result
    except Exception as e:
        return f"Error in exponential: {e}"


# Rounding and Absolute Value
@mcp.tool(name="abs", description="Calculate absolute value of a number")
def abs_value(x: float) -> float:
    """Calculate absolute value of x."""
    try:
        result = abs(x)
        return result
    except Exception as e:
        return f"Error in absolute value: {e}"


@mcp.tool(name="round", description="Round a number to specified decimal places")
def round_number(x: float, decimals: int = 0) -> float:
    """Round x to specified number of decimal places."""
    try:
        result = round(x, decimals)
        return result
    except Exception as e:
        return f"Error in rounding: {e}"


@mcp.tool(name="floor", description="Calculate floor (round down) of a number")
def floor(x: float) -> int:
    """Calculate floor of x."""
    try:
        result = math.floor(x)
        return result
    except Exception as e:
        return f"Error in floor: {e}"


@mcp.tool(name="ceil", description="Calculate ceiling (round up) of a number")
def ceil(x: float) -> int:
    """Calculate ceiling of x."""
    try:
        result = math.ceil(x)
        return result
    except Exception as e:
        return f"Error in ceiling: {e}"


# Factorial and Combinations
@mcp.tool(name="factorial", description="Calculate factorial of a non-negative integer")
def factorial(n: int) -> int:
    """Calculate factorial of n."""
    try:
        if n < 0:
            return "Error: Factorial is not defined for negative numbers"
        if n > 170:
            return "Error: Factorial too large to calculate"
        result = math.factorial(n)
        return result
    except Exception as e:
        return f"Error in factorial: {e}"


@mcp.tool(name="gcd", description="Calculate greatest common divisor of two integers")
def gcd(a: int, b: int) -> int:
    """Calculate greatest common divisor of a and b."""
    try:
        result = math.gcd(a, b)
        return result
    except Exception as e:
        return f"Error in GCD: {e}"


@mcp.tool(name="lcm", description="Calculate least common multiple of two integers")
def lcm(a: int, b: int) -> int:
    """Calculate least common multiple of a and b."""
    try:
        result = abs(a * b) // math.gcd(a, b) if a != 0 and b != 0 else 0
        return result
    except Exception as e:
        return f"Error in LCM: {e}"


# Statistical Functions
@mcp.tool(name="average", description="Calculate average of a list of numbers")
def average(numbers: str) -> float:
    """Calculate average of comma-separated numbers."""
    try:
        nums = [float(x.strip()) for x in numbers.split(",")]
        if not nums:
            return "Error: No numbers provided"
        result = sum(nums) / len(nums)
        return result
    except Exception as e:
        return f"Error in average: {e}"


@mcp.tool(name="max", description="Find maximum from a list of numbers")
def maximum(numbers: str) -> float:
    """Find maximum from comma-separated numbers."""
    try:
        nums = [float(x.strip()) for x in numbers.split(",")]
        if not nums:
            return "Error: No numbers provided"
        result = max(nums)
        return result
    except Exception as e:
        return f"Error in max: {e}"


@mcp.tool(name="min", description="Find minimum from a list of numbers")
def minimum(numbers: str) -> float:
    """Find minimum from comma-separated numbers."""
    try:
        nums = [float(x.strip()) for x in numbers.split(",")]
        if not nums:
            return "Error: No numbers provided"
        result = min(nums)
        return result
    except Exception as e:
        return f"Error in min: {e}"


mcp.run()

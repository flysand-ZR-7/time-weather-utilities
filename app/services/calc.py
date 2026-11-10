"""Safe AST-based mathematical evaluator and financial calculation engine."""

import ast
import math
import operator
from typing import Any, Callable, Dict, Union

# Whitelist allowed constants
MATH_CONSTANTS: Dict[str, float] = {
    "pi": math.pi,
    "e": math.e,
    "tau": math.tau,
}

# Whitelist allowed math functions
MATH_FUNCTIONS: Dict[str, Callable[..., Any]] = {
    "sqrt": math.sqrt,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "asin": math.asin,
    "acos": math.acos,
    "atan": math.atan,
    "log": math.log,
    "log10": math.log10,
    "log2": math.log2,
    "exp": math.exp,
    "abs": abs,
    "round": round,
    "floor": math.floor,
    "ceil": math.ceil,
    "factorial": math.factorial,
    "min": min,
    "max": max,
}

# Supported binary operators
BINARY_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

# Supported unary operators
UNARY_OPS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


def _guarded_pow(base: Union[int, float], exp: Union[int, float]) -> Union[int, float]:
    """Calculate base ** exp with overflow and CPU resource limits."""
    if abs(exp) > 1000:
        raise ValueError(f"Exponent {exp} exceeds safe maximum magnitude of 1000.")

    if base != 0 and abs(exp) > 0:
        try:
            log_magnitude = math.log10(abs(base)) * exp
            if log_magnitude > 300:
                raise ValueError("Calculation result exceeds numerical float limits (~10^308).")
        except OverflowError:
            raise ValueError("Calculation would overflow numerical limits.")

    try:
        res = base ** exp
        if isinstance(res, complex):
            raise ValueError("Complex numbers are not supported (e.g., negative base with fractional exponent).")
        return res
    except OverflowError:
        raise ValueError("Power computation resulted in numeric overflow.")


def _guarded_factorial(n: Any) -> int:
    """Calculate factorial with non-negative integer guard and upper limit of 170."""
    if not isinstance(n, (int, float)) or int(n) != n:
        raise ValueError("Factorial argument must be an integer.")
    n_int = int(n)
    if n_int < 0:
        raise ValueError("Factorial is not defined for negative numbers.")
    if n_int > 170:
        raise ValueError(f"Factorial argument {n_int} exceeds safe limit of 170 (171! overflows standard float).")
    return math.factorial(n_int)


class SafeEvaluator(ast.NodeVisitor):
    """Evaluates an AST expression strictly using whitelisted mathematical operations."""

    def visit(self, node: ast.AST) -> Any:
        method = "visit_" + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node: ast.AST) -> Any:
        raise ValueError(f"Unsupported syntax or expression element: {node.__class__.__name__}")

    def visit_Expression(self, node: ast.Expression) -> Any:
        return self.visit(node.body)

    def visit_Constant(self, node: ast.Constant) -> Union[int, float]:
        if isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
            return node.value
        raise ValueError(f"Literal constants must be numbers, got {type(node.value).__name__}.")

    def visit_Name(self, node: ast.Name) -> float:
        name = node.id.lower()
        if name in MATH_CONSTANTS:
            return MATH_CONSTANTS[name]
        raise ValueError(f"Undefined variable or constant '{node.id}'. Supported: {', '.join(MATH_CONSTANTS.keys())}")

    def visit_UnaryOp(self, node: ast.UnaryOp) -> Union[int, float]:
        op_type = type(node.op)
        if op_type not in UNARY_OPS:
            raise ValueError(f"Unary operator '{op_type.__name__}' is not permitted.")
        operand = self.visit(node.operand)
        return UNARY_OPS[op_type](operand)

    def visit_BinOp(self, node: ast.BinOp) -> Union[int, float]:
        op_type = type(node.op)
        if op_type not in BINARY_OPS:
            raise ValueError(f"Binary operator '{op_type.__name__}' is not permitted.")

        left = self.visit(node.left)
        right = self.visit(node.right)

        if op_type in (ast.Div, ast.FloorDiv, ast.Mod) and right == 0:
            raise ZeroDivisionError("Division or modulo by zero is undefined.")

        if op_type is ast.Pow:
            return _guarded_pow(left, right)

        try:
            return BINARY_OPS[op_type](left, right)
        except OverflowError:
            raise ValueError("Arithmetic operation resulted in numeric overflow.")

    def visit_Call(self, node: ast.Call) -> Any:
        if not isinstance(node.func, ast.Name):
            raise ValueError("Only direct mathematical function calls are supported.")

        fn_name = node.func.id.lower()
        if fn_name not in MATH_FUNCTIONS:
            raise ValueError(
                f"Function '{node.func.id}' is not permitted. "
                f"Supported functions: {', '.join(sorted(MATH_FUNCTIONS.keys()))}"
            )

        if node.keywords:
            raise ValueError("Keyword arguments are not supported in function calls.")

        args = [self.visit(arg) for arg in node.args]

        if fn_name == "factorial":
            if len(args) != 1:
                raise ValueError("factorial takes exactly 1 argument.")
            return _guarded_factorial(args[0])

        try:
            res = MATH_FUNCTIONS[fn_name](*args)
            if isinstance(res, float) and (math.isnan(res) or math.isinf(res)):
                raise ValueError(f"Function '{fn_name}' resulted in an undefined or infinite value.")
            return res
        except (ValueError, TypeError, OverflowError) as exc:
            raise ValueError(f"Domain error or invalid arguments for function '{fn_name}': {str(exc)}")


def evaluate_expression(expression: str) -> Dict[str, Any]:
    """Safely parse and evaluate a mathematical expression without eval() or exec()."""
    clean_expr = expression.strip()
    if not clean_expr:
        raise ValueError("Expression cannot be empty.")

    # Preprocess caret '^' to '**' for power operations
    normalized_expr = clean_expr.replace("^", "**")

    try:
        tree = ast.parse(normalized_expr, mode="eval")
    except SyntaxError as syn_err:
        raise ValueError(f"Syntax error in expression: {syn_err.msg} at position {syn_err.offset}")

    evaluator = SafeEvaluator()
    raw_result = evaluator.visit(tree)

    # Format result for human presentation
    if isinstance(raw_result, float):
        if raw_result.is_integer() and abs(raw_result) < 1e15:
            formatted = str(int(raw_result))
            val: Union[int, float] = int(raw_result)
        elif abs(raw_result) >= 1e15 or (0 < abs(raw_result) < 1e-6):
            formatted = f"{raw_result:.6e}"
            val = round(raw_result, 10)
        else:
            val = round(raw_result, 10)
            formatted = f"{val:.10g}"
    else:
        val = raw_result
        formatted = str(raw_result)

    return {
        "expression": clean_expr,
        "result": val,
        "formatted": formatted,
    }


def calculate_finance(
    operation: str,
    amount: Optional[float] = None,
    percent: Optional[float] = None,
    value: Optional[float] = None,
    total: Optional[float] = None,
    old_value: Optional[float] = None,
    new_value: Optional[float] = None,
    original_price: Optional[float] = None,
    discount_percent: Optional[float] = None,
    tax_percent: Optional[float] = None,
    tax_included: bool = False,
    bill_amount: Optional[float] = None,
    tip_percent: Optional[float] = None,
    num_people: int = 1,
    principal: Optional[float] = None,
    rate_annual_percent: Optional[float] = None,
    time_years: Optional[float] = None,
    compounding_frequency: int = 12,
    tenure_months: Optional[int] = None,
) -> Dict[str, Any]:
    """Perform financial calculations: discounts, taxes, tips, interest, and loan EMI."""
    op = operation.lower().strip()

    if op == "percentage":
        # Check sub-modes: percent_of, what_percent, percentage_change
        if percent is not None and value is not None:
            calc_val = (percent / 100.0) * value
            return {
                "operation": "percentage",
                "sub_type": "percent_of",
                "percent": percent,
                "value": value,
                "result": round(calc_val, 4),
                "explanation": f"{percent}% of {value} is {round(calc_val, 4)}",
            }
        elif value is not None and total is not None:
            if total == 0:
                raise ZeroDivisionError("Total cannot be zero when calculating percentage share.")
            calc_pct = (value / total) * 100.0
            return {
                "operation": "percentage",
                "sub_type": "what_percent",
                "value": value,
                "total": total,
                "result": round(calc_pct, 4),
                "explanation": f"{value} is {round(calc_pct, 2)}% of {total}",
            }
        elif old_value is not None and new_value is not None:
            if old_value == 0:
                raise ZeroDivisionError("Original value cannot be zero when calculating percentage change.")
            pct_change = ((new_value - old_value) / abs(old_value)) * 100.0
            direction = "increase" if pct_change > 0 else ("decrease" if pct_change < 0 else "no change")
            return {
                "operation": "percentage",
                "sub_type": "percentage_change",
                "old_value": old_value,
                "new_value": new_value,
                "result": round(pct_change, 4),
                "direction": direction,
                "explanation": f"From {old_value} to {new_value} is a {abs(round(pct_change, 2))}% {direction}",
            }
        else:
            raise ValueError("Provide either (percent, value), (value, total), or (old_value, new_value) for percentage.")

    elif op == "discount":
        if original_price is None or discount_percent is None:
            raise ValueError("original_price and discount_percent are required for discount calculation.")
        if original_price < 0 or discount_percent < 0:
            raise ValueError("Prices and percentages cannot be negative.")

        savings = original_price * (discount_percent / 100.0)
        discounted_price = original_price - savings

        tax_amt = 0.0
        tax_pct = tax_percent or 0.0
        if tax_pct > 0:
            tax_amt = discounted_price * (tax_pct / 100.0)

        final_price = discounted_price + tax_amt

        return {
            "operation": "discount",
            "original_price": round(original_price, 2),
            "discount_percent": discount_percent,
            "savings": round(savings, 2),
            "discounted_price": round(discounted_price, 2),
            "tax_percent": tax_pct,
            "tax_amount": round(tax_amt, 2),
            "final_price": round(final_price, 2),
        }

    elif op == "tax":
        amt = amount if amount is not None else original_price
        pct = tax_percent if tax_percent is not None else percent
        if amt is None or pct is None:
            raise ValueError("amount and tax_percent are required for tax calculation.")
        if amt < 0 or pct < 0:
            raise ValueError("Amount and tax rate cannot be negative.")

        if tax_included:
            net = amt / (1.0 + pct / 100.0)
            tax_amt = amt - net
            gross = amt
        else:
            net = amt
            tax_amt = amt * (pct / 100.0)
            gross = amt + tax_amt

        return {
            "operation": "tax",
            "net_amount": round(net, 2),
            "tax_rate_percent": pct,
            "tax_amount": round(tax_amt, 2),
            "gross_amount": round(gross, 2),
            "tax_included": tax_included,
        }

    elif op == "tip_split":
        if bill_amount is None or tip_percent is None:
            raise ValueError("bill_amount and tip_percent are required for tip split calculation.")
        if bill_amount < 0 or tip_percent < 0:
            raise ValueError("Bill amount and tip percentage cannot be negative.")
        if num_people < 1:
            raise ValueError("Number of people must be at least 1.")

        tip_total = bill_amount * (tip_percent / 100.0)
        total_bill = bill_amount + tip_total

        return {
            "operation": "tip_split",
            "bill_amount": round(bill_amount, 2),
            "tip_percent": tip_percent,
            "tip_amount": round(tip_total, 2),
            "total_amount": round(total_bill, 2),
            "num_people": num_people,
            "per_person_total": round(total_bill / num_people, 2),
            "per_person_bill": round(bill_amount / num_people, 2),
            "per_person_tip": round(tip_total / num_people, 2),
        }

    elif op == "simple_interest":
        if principal is None or rate_annual_percent is None or time_years is None:
            raise ValueError("principal, rate_annual_percent, and time_years are required for simple interest.")
        if principal < 0 or rate_annual_percent < 0 or time_years < 0:
            raise ValueError("Values cannot be negative.")

        interest = principal * (rate_annual_percent / 100.0) * time_years
        total_amt = principal + interest

        return {
            "operation": "simple_interest",
            "principal": round(principal, 2),
            "rate_annual_percent": rate_annual_percent,
            "time_years": time_years,
            "interest": round(interest, 2),
            "total_amount": round(total_amt, 2),
        }

    elif op == "compound_interest":
        if principal is None or rate_annual_percent is None or time_years is None:
            raise ValueError("principal, rate_annual_percent, and time_years are required for compound interest.")
        if principal < 0 or rate_annual_percent < 0 or time_years < 0:
            raise ValueError("Values cannot be negative.")
        if compounding_frequency <= 0:
            raise ValueError("Compounding frequency must be greater than 0.")

        r = rate_annual_percent / 100.0
        n = compounding_frequency
        t = time_years

        total_amt = principal * ((1.0 + r / n) ** (n * t))
        interest = total_amt - principal
        ear = (((1.0 + r / n) ** n) - 1.0) * 100.0

        return {
            "operation": "compound_interest",
            "principal": round(principal, 2),
            "rate_annual_percent": rate_annual_percent,
            "time_years": time_years,
            "compounding_frequency": compounding_frequency,
            "interest": round(interest, 2),
            "total_amount": round(total_amt, 2),
            "effective_annual_rate_percent": round(ear, 4),
        }

    elif op == "emi":
        if principal is None or rate_annual_percent is None or tenure_months is None:
            raise ValueError("principal, rate_annual_percent, and tenure_months are required for EMI calculation.")
        if principal <= 0:
            raise ValueError("Principal must be greater than 0.")
        if rate_annual_percent < 0 or tenure_months <= 0:
            raise ValueError("Interest rate and tenure months must be positive.")

        monthly_rate = (rate_annual_percent / 100.0) / 12.0
        if monthly_rate == 0:
            monthly_emi = principal / tenure_months
        else:
            comp = (1.0 + monthly_rate) ** tenure_months
            monthly_emi = principal * monthly_rate * comp / (comp - 1.0)

        total_paid = monthly_emi * tenure_months
        total_interest = total_paid - principal

        return {
            "operation": "emi",
            "principal": round(principal, 2),
            "annual_interest_rate_percent": rate_annual_percent,
            "tenure_months": tenure_months,
            "monthly_emi": round(monthly_emi, 2),
            "total_interest": round(total_interest, 2),
            "total_payment": round(total_paid, 2),
        }

    else:
        raise ValueError(
            f"Unsupported financial operation '{operation}'. Supported: "
            "'percentage', 'discount', 'tax', 'tip_split', 'simple_interest', 'compound_interest', 'emi'."
        )

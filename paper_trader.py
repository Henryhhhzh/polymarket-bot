from dataclasses import dataclass


@dataclass
class PaperQuote:
    bid_price: float
    ask_price: float
    order_size: float
    mode: str


@dataclass
class PaperAccount:
    cash: float
    yes_inventory: float = 0.0
    avg_entry_price: float = 0.0


def calculate_paper_quote(
    mid_price: float,
    quote_width: float,
    order_size: float,
    mode: str,
) -> PaperQuote:
    bid_price = max(mid_price - quote_width, 0.01)
    ask_price = min(mid_price + quote_width, 0.99)

    return PaperQuote(
        bid_price=round(bid_price, 3),
        ask_price=round(ask_price, 3),
        order_size=order_size,
        mode=mode,
    )


def simulate_paper_fills(
    account: PaperAccount,
    quote: PaperQuote,
    later_best_bid: float,
    later_best_ask: float,
) -> dict:
    filled_bid = False
    filled_ask = False

    if later_best_ask <= quote.bid_price:
        cost = quote.bid_price * quote.order_size

        if account.cash >= cost:
            old_inventory_value = account.avg_entry_price * account.yes_inventory

            account.cash -= cost
            account.yes_inventory += quote.order_size

            new_inventory_value = old_inventory_value + cost
            account.avg_entry_price = new_inventory_value / account.yes_inventory

            filled_bid = True

    if later_best_bid >= quote.ask_price and account.yes_inventory >= quote.order_size:
        revenue = quote.ask_price * quote.order_size

        account.cash += revenue
        account.yes_inventory -= quote.order_size

        if account.yes_inventory == 0:
            account.avg_entry_price = 0.0

        filled_ask = True

    estimated_position_value = account.yes_inventory * later_best_bid
    estimated_total_value = account.cash + estimated_position_value

    return {
        "filled_bid": filled_bid,
        "filled_ask": filled_ask,
        "cash": round(account.cash, 3),
        "yes_inventory": round(account.yes_inventory, 3),
        "avg_entry_price": round(account.avg_entry_price, 3),
        "estimated_position_value": round(estimated_position_value, 3),
        "estimated_total_value": round(estimated_total_value, 3),
    }


def print_paper_quote(quote: PaperQuote) -> None:
    print("=" * 80)
    print("PAPER QUOTE")
    print("Mode:", quote.mode)
    print("Bid price:", quote.bid_price)
    print("Ask price:", quote.ask_price)
    print("Order size:", quote.order_size)
    print("No real order was placed.")


def print_paper_account(account: PaperAccount, estimated_total_value: float) -> None:
    print("=" * 80)
    print("PAPER ACCOUNT")
    print("Cash:", round(account.cash, 3))
    print("YES inventory:", round(account.yes_inventory, 3))
    print("Average entry:", round(account.avg_entry_price, 3))
    print("Estimated total value:", round(estimated_total_value, 3))
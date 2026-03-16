"""
Market clearing — tâtonnement price adjustment toward equilibrium.

Agents are buyers and sellers with reservation prices and inventories.
A global price adjusts iteratively toward supply–demand equilibrium.
Transactions occur when buyer reservation ≥ market price ≥ seller
reservation.

Priors from microeconomics (Walrasian equilibrium, Vernon Smith's
double-auction experiments).
"""

from __future__ import annotations

import numpy as np

from ...dynamics.graph import DynamicsGraph
from ...dynamics.models import EdgeType, NodeType
from .base import DynamicsTemplate, ParameterSpec


class MarketClearingTemplate(DynamicsTemplate):
    name = "market_clearing"
    description = "Tâtonnement price adjustment with buyer/seller reservation prices"
    required_node_types = []
    required_edge_types = []
    parameters = {
        "price_adjustment_speed": ParameterSpec(
            0.1, 0.01, 1.0,
            "Speed of price convergence toward equilibrium",
        ),
        "elasticity": ParameterSpec(
            1.0, 0.1, 5.0,
            "Price elasticity of demand",
        ),
        "transaction_cost": ParameterSpec(
            0.02, 0.0, 0.5,
            "Friction cost per transaction",
        ),
    }

    def update(
        self,
        graph: DynamicsGraph,
        params: dict[str, float],
        rng: np.random.Generator,
    ) -> None:
        p = self.validate_params(params)
        speed = p["price_adjustment_speed"]
        elasticity = p["elasticity"]
        tx_cost = p["transaction_cost"]

        agents = list(graph.nodes_by_type(NodeType.AGENT))
        institutions = list(graph.nodes_by_type(NodeType.INSTITUTION))
        participants = agents + institutions
        if not participants:
            return

        # --- Bootstrap ---
        for node in participants:
            if "reservation_price" not in node.state.custom:
                node.state.custom["reservation_price"] = float(
                    rng.uniform(0.5, 2.0)
                )
            if "inventory" not in node.state.custom:
                node.state.custom["inventory"] = float(rng.uniform(0.0, 5.0))
            if "is_seller" not in node.state.custom:
                # Roughly half sellers, half buyers
                node.state.custom["is_seller"] = float(rng.random() > 0.5)

        # Global market price (stored on first participant or bootstrapped)
        market_price_key = "market_price"
        price_node = participants[0]
        if market_price_key not in price_node.state.custom:
            price_node.state.custom[market_price_key] = 1.0
        market_price = price_node.state.custom[market_price_key]

        # --- Phase 1: Compute supply and demand ---
        supply = 0.0
        demand = 0.0
        sellers = []
        buyers = []

        for node in participants:
            res_price = node.state.custom.get("reservation_price", 1.0)
            inv = node.state.custom.get("inventory", 0.0)

            if node.state.custom.get("is_seller", 0.0) > 0.5:
                # Seller: willing to sell if market price >= reservation
                if market_price >= res_price and inv > 0:
                    qty = min(inv, inv * (market_price / res_price) ** elasticity)
                    supply += qty
                    sellers.append((node, qty))
            else:
                # Buyer: willing to buy if reservation >= market price
                if res_price >= market_price:
                    qty = (res_price / max(0.01, market_price)) ** elasticity
                    qty = min(qty, node.state.resources / max(0.01, market_price))
                    demand += qty
                    buyers.append((node, qty))

        # --- Phase 2: Tâtonnement price adjustment ---
        excess_demand = demand - supply
        new_price = max(0.01, market_price + speed * excess_demand * 0.1)
        price_node.state.custom[market_price_key] = new_price

        # Broadcast price to all participants
        for node in participants:
            node.state.custom["current_market_price"] = new_price

        # --- Phase 3: Execute transactions ---
        # Match buyers and sellers
        rng.shuffle(buyers)
        rng.shuffle(sellers)

        bi, si = 0, 0
        while bi < len(buyers) and si < len(sellers):
            buyer, b_qty = buyers[bi]
            seller, s_qty = sellers[si]

            trade_qty = min(b_qty, s_qty)
            if trade_qty <= 0:
                bi += 1
                continue

            cost = trade_qty * market_price * (1.0 + tx_cost)
            if buyer.state.resources < cost:
                bi += 1
                continue

            # Execute
            buyer.state.resources -= cost
            seller.state.resources += trade_qty * market_price * (1.0 - tx_cost)
            buyer.state.custom["inventory"] = (
                buyer.state.custom.get("inventory", 0.0) + trade_qty
            )
            seller.state.custom["inventory"] = max(
                0.0, seller.state.custom.get("inventory", 0.0) - trade_qty
            )

            buyers[bi] = (buyer, b_qty - trade_qty)
            sellers[si] = (seller, s_qty - trade_qty)

            if b_qty - trade_qty <= 0:
                bi += 1
            if s_qty - trade_qty <= 0:
                si += 1

"""
This is the reference implementation of the Almgren-Chriss optimal order execution algorithm.
See ae-optimal-order-execution.py for the AlphaEvolve(d) algorithm.
the paper: https://www.smallake.kr/wp-content/uploads/2016/03/optliq.pdf
"""

import numpy as np
from typing import List, Tuple
from optimal_order_execution import MarketSimulator

def execute_large_order(total_size: float, time_horizon: int, market: MarketSimulator) -> List[Tuple[float, float]]:
    """Almgren-Chriss optimal execution strategy."""
    orders = []
    remaining_size = total_size
    
    # Get initial market state
    state = market.get_market_state()
    volatility = state['volatility']
    
    # A-C parameters
    eta = 0.01    # Permanent impact
    gamma = 0.1   # Temporary impact
    risk_aversion = 1e-6
    
    # Optimal trading rate decay
    kappa = np.sqrt(risk_aversion * volatility**2 / (eta * gamma))
    
    for t in range(time_horizon):
        if remaining_size <= 0:
            break
            
        tau = time_horizon - t
        
        if tau > 0:
            trade_rate = (2 * kappa * remaining_size) / (1 - np.exp(-2 * kappa * tau))
            order_size = min(trade_rate, remaining_size)
        else:
            order_size = remaining_size
            
        if order_size > 0:
            orders.append((t, order_size))
            remaining_size -= order_size
            market.execute_order(order_size)
    
    if remaining_size > 0:
        orders.append((time_horizon-1, remaining_size))
        market.execute_order(remaining_size)
    
    return orders
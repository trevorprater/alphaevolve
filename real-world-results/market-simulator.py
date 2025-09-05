"""
Enhanced evaluator for optimal order execution with adversarial scenarios.
Designed to discover strategies that outperform Almgren-Chriss.
"""

import numpy as np
from typing import Tuple, Dict, Any, List
import importlib.util
import sys
from optimal_order_execution import MarketSimulator


def evaluate(program_namespace_or_code, **kwargs) -> Tuple[float, Dict[str, int], Dict[str, Any]]:
    """
    Enhanced evaluation with challenging scenarios to beat Almgren-Chriss.
    
    Returns:
        - fitness: Implementation shortfall (lower is better)  
        - features: Algorithm characteristics for MAP-Elites
        - metadata: Detailed performance metrics
    """
    # Handle both namespace dict and code string inputs
    if isinstance(program_namespace_or_code, dict):
        namespace = program_namespace_or_code
        class ModuleProxy:
            def __init__(self, ns):
                self.__dict__.update(ns)
        module = ModuleProxy(namespace)
    else:
        code = str(program_namespace_or_code)
        spec = importlib.util.spec_from_loader("evolved_module", loader=None)
        module = importlib.util.module_from_spec(spec)
        sys.modules["evolved_module"] = module
        exec(code, module.__dict__)
    
    # Enhanced test scenarios designed to break Almgren-Chriss
    test_scenarios = [
        # Standard scenarios (but with more variation)
        {"name": "normal", "size": 10000, "horizon": 100, "volatility": 0.02, 
         "liquidity": 100000, "spread_mean": 0.0001, "spread_vol": 0.00005,
         "momentum": 0.0, "mean_reversion": 0.0, "adverse_selection": 0.0},
        
        {"name": "large_order", "size": 50000, "horizon": 200, "volatility": 0.03,
         "liquidity": 200000, "spread_mean": 0.0002, "spread_vol": 0.0001,
         "momentum": 0.0, "mean_reversion": 0.0, "adverse_selection": 0.0},
        
        # Challenging scenarios where Almgren-Chriss struggles
        {"name": "momentum_market", "size": 20000, "horizon": 100, "volatility": 0.025,
         "liquidity": 100000, "spread_mean": 0.0001, "spread_vol": 0.00005,
         "momentum": 0.0003, "mean_reversion": 0.0, "adverse_selection": 0.0},
        
        {"name": "mean_reverting", "size": 15000, "horizon": 150, "volatility": 0.02,
         "liquidity": 150000, "spread_mean": 0.0001, "spread_vol": 0.00005,
         "momentum": 0.0, "mean_reversion": 0.01, "adverse_selection": 0.0},
        
        {"name": "toxic_flow", "size": 25000, "horizon": 80, "volatility": 0.035,
         "liquidity": 80000, "spread_mean": 0.0003, "spread_vol": 0.0002,
         "momentum": 0.0, "mean_reversion": 0.0, "adverse_selection": 0.002},
        
        {"name": "flash_crash", "size": 10000, "horizon": 50, "volatility": 0.08,
         "liquidity": 30000, "spread_mean": 0.001, "spread_vol": 0.0008,
         "momentum": -0.001, "mean_reversion": 0.0, "adverse_selection": 0.003},
        
        {"name": "closing_auction", "size": 30000, "horizon": 30, "volatility": 0.04,
         "liquidity": 150000, "spread_mean": 0.0002, "spread_vol": 0.0001,
         "momentum": 0.0, "mean_reversion": 0.02, "adverse_selection": 0.0},
        
        {"name": "predatory_hft", "size": 15000, "horizon": 120, "volatility": 0.025,
         "liquidity": 100000, "spread_mean": 0.0002, "spread_vol": 0.0001,
         "momentum": 0.0, "mean_reversion": 0.0, "adverse_selection": 0.0015},
    ]
    
    total_shortfall = 0
    total_risk = 0
    scenario_results = {}
    robustness_score = 0
    
    for scenario in test_scenarios:
        scenario_shortfalls = []
        scenario_costs = []
        
        # Run multiple trials per scenario with different seeds
        for trial in range(3):  # Reduced trials for speed
            seed = abs(hash(scenario['name'])) % 1000000 * 100 + trial
            np.random.seed(seed)
            
            # Create enhanced market simulator
            market = EnhancedMarketSimulator(
                base_price=100.0,
                volatility=scenario['volatility'],
                liquidity_depth=scenario['liquidity'],
                spread_mean=scenario['spread_mean'],
                spread_volatility=scenario['spread_vol'],
                momentum_factor=scenario['momentum'],
                mean_reversion_speed=scenario['mean_reversion'],
                adverse_selection_factor=scenario['adverse_selection']
            )
            
            arrival_price = market.current_price
            arrival_spread = market.current_spread
            
            try:
                # Try different evolved functions
                if hasattr(module, 'execute_with_predictions'):
                    orders = module.execute_with_predictions(
                        scenario['size'], scenario['horizon'], market)
                elif hasattr(module, 'execute_with_market_conditions'):
                    orders = module.execute_with_market_conditions(
                        scenario['size'], scenario['horizon'], market)
                else:
                    orders = module.execute_large_order(
                        scenario['size'], scenario['horizon'], market)
                
                # Validate orders
                if not isinstance(orders, list):
                    return float('inf'), {"complexity": 0, "adaptivity": 0}, {"error": "Invalid orders format"}
                
                total_order_size = sum(order_size for _, order_size in orders if order_size > 0)
                if abs(total_order_size - scenario['size']) > 1e-6:
                    return float('inf'), {"complexity": 0, "adaptivity": 0}, {"error": f"Order size mismatch: {total_order_size} vs {scenario['size']}"}
                
                # Reset market and execute
                market = EnhancedMarketSimulator(
                    base_price=100.0,
                    volatility=scenario['volatility'],
                    liquidity_depth=scenario['liquidity'],
                    spread_mean=scenario['spread_mean'],
                    spread_volatility=scenario['spread_vol'],
                    momentum_factor=scenario['momentum'],
                    mean_reversion_speed=scenario['mean_reversion'],
                    adverse_selection_factor=scenario['adverse_selection']
                )
                
                total_cost = 0
                executed_size = 0
                execution_prices = []
                spread_costs = 0
                
                for t, order_size in orders:
                    if order_size > 0:
                        # Execute with enhanced market dynamics
                        exec_price, paid_spread = market.execute_order_with_spread(order_size)
                        total_cost += exec_price * order_size
                        executed_size += order_size
                        execution_prices.append(exec_price)
                        spread_costs += paid_spread * order_size
                
                # Verify execution
                if abs(executed_size - scenario['size']) > 1e-6:
                    return float('inf'), {"complexity": 0, "adaptivity": 0}, {"error": "Incomplete execution"}
                
                # Calculate implementation shortfall
                avg_exec_price = total_cost / executed_size
                impl_shortfall = (avg_exec_price - arrival_price) / arrival_price
                scenario_shortfalls.append(impl_shortfall)
                scenario_costs.append(total_cost)
                
            except Exception as e:
                return float('inf'), {"complexity": 0, "adaptivity": 0}, {"error": str(e)}
        
        # Store scenario results
        avg_shortfall = np.mean(scenario_shortfalls)
        scenario_risk = np.std(scenario_shortfalls)
        scenario_results[scenario['name']] = {
            'shortfall': avg_shortfall,
            'risk': scenario_risk,
            'sharpe': -avg_shortfall / scenario_risk if scenario_risk > 0 else -avg_shortfall * 100
        }
        
        # Weight challenging scenarios more heavily
        weight = 2.0 if scenario['name'] in ['momentum_market', 'toxic_flow', 
                                              'flash_crash', 'predatory_hft'] else 1.0
        total_shortfall += avg_shortfall * weight
        total_risk += scenario_risk * weight
        
        # Robustness: Penalize high variance in challenging scenarios  
        if scenario['name'] in ['flash_crash', 'predatory_hft']:
            robustness_score += scenario_risk * 10
    
    # Calculate aggregate metrics
    weights_sum = 11.0  # 8 scenarios, 4 with double weight
    avg_shortfall = total_shortfall / weights_sum
    avg_risk = total_risk / weights_sum
    
    # Fitness combines shortfall and robustness
    fitness = avg_shortfall * 1000  # Scale for discrimination
    fitness += avg_risk * 200  # Penalize high variance
    fitness += robustness_score  # Extra penalty for failing in adverse scenarios
    
    # Reward beating Almgren-Chriss baseline (87.28 bps = 0.008728)
    if avg_shortfall < 0.008728:
        fitness *= 0.9  # 10% bonus for beating baseline
    
    # Feature extraction for diversity
    # Analyze strategy characteristics
    order_sizes = []
    order_times = []
    for orders_list in [orders]:
        for t, size in orders_list:
            if size > 0:
                order_sizes.append(size)
                order_times.append(t)
    
    # Feature 1: Execution aggressiveness (front-loaded vs back-loaded)
    if len(order_times) > 1:
        total_time = max(order_times) - min(order_times) + 1
        front_weight = sum(1 for t in order_times if t < total_time / 3) / len(order_times)
        aggressiveness = int(front_weight * 10)  # 0-10 scale
    else:
        aggressiveness = 5
    
    # Feature 2: Adaptiveness (variation in order sizes)
    if len(order_sizes) > 1:
        size_cv = np.std(order_sizes) / np.mean(order_sizes)
        adaptiveness = min(10, int(size_cv * 20))
    else:
        adaptiveness = 0
    
    features = {
        "aggressiveness": aggressiveness,
        "adaptiveness": adaptiveness
    }
    
    # Detailed metadata
    metadata = {
        "avg_impl_shortfall": avg_shortfall,
        "avg_risk": avg_risk,
        "robustness_score": robustness_score,
        "scenario_results": scenario_results,
        "beats_almgren_chriss": avg_shortfall < 0.008728,
        "improvement_over_ac": (0.008728 - avg_shortfall) / 0.008728 * 100 if avg_shortfall < 0.008728 else 0
    }
    
    return fitness, features, metadata


class EnhancedMarketSimulator:
    """Enhanced market simulator with realistic microstructure."""
    
    def __init__(self, base_price=100.0, volatility=0.02, liquidity_depth=100000,
                 spread_mean=0.0001, spread_volatility=0.00005,
                 momentum_factor=0.0, mean_reversion_speed=0.0,
                 adverse_selection_factor=0.0):
        self.base_price = base_price
        self.current_price = base_price
        self.volatility = volatility
        self.liquidity_depth = liquidity_depth
        self.spread_mean = spread_mean
        self.spread_volatility = spread_volatility
        self.momentum_factor = momentum_factor
        self.mean_reversion_speed = mean_reversion_speed
        self.adverse_selection_factor = adverse_selection_factor
        
        self.time = 0
        self.execution_history = []
        self.price_history = [base_price]
        self.current_spread = spread_mean
        self.total_volume = 0
        
    def get_market_state(self) -> Dict[str, float]:
        """Get current market conditions with microstructure details."""
        # Calculate recent momentum
        if len(self.price_history) > 5:
            recent_return = (self.price_history[-1] - self.price_history[-5]) / self.price_history[-5]
        else:
            recent_return = 0
            
        # Order flow imbalance (simulated)
        imbalance = np.random.normal(0, 0.3)
        
        return {
            'price': self.current_price,
            'spread': self.current_spread,
            'volatility': self.volatility,
            'bid': self.current_price - self.current_spread / 2,
            'ask': self.current_price + self.current_spread / 2,
            'recent_momentum': recent_return,
            'order_flow_imbalance': imbalance,
            'time_of_day': self.time,
            'total_volume': self.total_volume
        }
    
    def execute_order_with_spread(self, size: float) -> Tuple[float, float]:
        """Execute order with realistic spread and market impact."""
        # Dynamic spread based on order size and market conditions
        size_factor = size / self.liquidity_depth
        self.current_spread = self.spread_mean * (1 + 10 * size_factor)
        self.current_spread *= (1 + np.random.normal(0, self.spread_volatility / self.spread_mean))
        
        # Pay half spread plus market impact
        spread_cost = self.current_spread / 2
        
        # Non-linear market impact (square-root law)
        temp_impact = 0.1 * np.sqrt(size / self.liquidity_depth)
        perm_impact = 0.01 * (size / self.liquidity_depth)
        
        # Adverse selection adds extra cost for toxic flow
        if self.adverse_selection_factor > 0:
            info_cost = self.adverse_selection_factor * size / self.liquidity_depth
            perm_impact += info_cost
        
        # Execute at impacted price
        exec_price = self.current_price * (1 + spread_cost + temp_impact + perm_impact)
        
        # Update price with permanent impact and market dynamics
        self.current_price *= (1 + perm_impact)
        
        # Add momentum
        if self.momentum_factor != 0:
            self.current_price *= (1 + self.momentum_factor)
        
        # Mean reversion
        if self.mean_reversion_speed > 0:
            self.current_price += self.mean_reversion_speed * (self.base_price - self.current_price)
        
        # Random walk component
        self.current_price *= (1 + np.random.normal(0, self.volatility / np.sqrt(252 * 390)))
        
        # Update history
        self.time += 1
        self.execution_history.append((exec_price, size))
        self.price_history.append(self.current_price)
        self.total_volume += size
        
        return exec_price, spread_cost
    
    def execute_order(self, size: float) -> float:
        """Backward compatibility method."""
        exec_price, _ = self.execute_order_with_spread(size)
        return exec_price
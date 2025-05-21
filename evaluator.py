# evaluator.py
def evaluate(program_code_string_or_module, **kwargs):
    """
    Evaluates the evolved code by calling my_block_logic with test inputs.
    
    Args:
        program_code_string_or_module: Either a dictionary containing the local namespace 
                                      after executing the evolved code, or a string of the code.
        **kwargs: Additional arguments (unused in this implementation).
        
    Returns:
        dict: A dictionary containing the evaluation results including 'objective' score
              and additional metrics or error information.
    """
    # Debug output to show what we're evaluating
    if isinstance(program_code_string_or_module, dict):
        namespace = program_code_string_or_module
        print(f"Evaluating namespace with keys: {list(namespace.keys())}")
        
        # Check if my_block_logic exists in the namespace
        if 'my_block_logic' not in namespace:
            print("Error: my_block_logic function not found in namespace")
            return {
                'objective': -float('inf'),
                'error': 'my_block_logic not found'
            }
        
        # Get the my_block_logic function from the namespace
        my_block_logic = namespace['my_block_logic']
        
        # Define test cases and expected outputs
        test_cases = [
            {'input_x': 5, 'current_val': 10, 'expected': 20},
            {'input_x': 3, 'current_val': 0, 'expected': 6}
        ]
        
        results = {}
        total_error = 0
        
        try:
            # Run the test cases
            for i, test in enumerate(test_cases, 1):
                output = my_block_logic(input_x=test['input_x'], current_val=test['current_val'])
                error = abs(output - test['expected'])
                total_error += error
                
                # Store the results
                results[f'output{i}'] = output
                results[f'expected{i}'] = test['expected']
                results[f'error{i}'] = error
            
            # Calculate the score (higher is better)
            # 1.0 / (1 + total error) ensures that the score is between 0 and 1,
            # and higher when the total error is lower
            score = 1.0 / (1.0 + total_error)
            
            # Add the score to the results
            results['objective'] = score
            
            return results
            
        except Exception as e:
            # Handle any exceptions from calling my_block_logic
            print(f"Error executing my_block_logic: {str(e)}")
            return {
                'objective': -float('inf'),
                'error': f'Error executing my_block_logic: {str(e)}'
            }
    else:
        # If we received a string instead of a namespace dictionary
        print(f"Evaluating: {program_code_string_or_module[:50]}...")
        print("Warning: Expected a namespace dictionary, received a string or other object")
        # Return a basic score based on length as a fallback
        return {
            'objective': -1.0,  # Negative score indicates this is not the preferred input format
            'length': float(len(str(program_code_string_or_module))),
            'error': 'Expected namespace dictionary, received different type'
        }